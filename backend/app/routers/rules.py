import json
import re
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db, get_db_session_factory
from app.models import ChatFeedback, ChatSession, Progress, RuleExplanation, User
from app.schemas.rules import (
    ChatFeedbackItemSchema,
    ChatFeedbackRequest,
    ChatHistoryResponse,
    ChatMessageSchema,
    ChatbotQueryRequest,
    GenerateAdditionalExercisesRequest,
    GenerateAdditionalExercisesResponse,
    RuleExplanationResponse,
    RuleListItemSchema,
    SubtopicSchema,
    TopicSchema,
)
from app.services.auth import get_current_user as get_authenticated_user
from app.services.llm import (
    generate_additional_exercises,
    generate_chatbot_answer,
    generate_spanish_explanation,
)
from app.services.rag import get_extended_context

router = APIRouter(
    prefix="/rule",
    tags=["rules"]
)

oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


async def get_current_user_or_guest(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Returns the authenticated user or falls back to a guest user if no valid token is provided."""
    if token:
        try:
            return await get_authenticated_user(token=token, db=db)
        except HTTPException:
            pass

    return User(id=0, email="guest@example.com", hashed_password="", current_level="A1")


def parse_chunk_id_for_sort(chunk_id: str) -> List[int]:
    """Extracts numeric indices from a chunk ID for natural sorting."""
    numbers = re.findall(r'\d+', chunk_id)
    return [int(n) for n in numbers]


@router.get("/search")
async def search_rule(
    query: str,
    lang: str = "en",
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_authenticated_user)
):
    """Searches rules using RAG and generates an explanation via LLM."""
    embedding_model = request.app.state.embedding_model
    collection = request.app.state.collection
    gemini_client = request.app.state.gemini_client

    context_data = await get_extended_context(
        query_text=query,
        collection=collection,
        model=embedding_model,
        user_level=current_user.current_level,
        n_results=15
    )

    if not context_data or not context_data['documents'] or not context_data['documents'][0]:
        raise HTTPException(status_code=404, detail="Corresponding rules not found.")

    full_context_text = ""
    for cid, text, meta in zip(
        context_data['ids'][0],
        context_data['documents'][0],
        context_data['metadatas'][0]
    ):
        level = meta.get('level', 'N/A')
        full_context_text += f"Block {cid} (Level {level}):\n{text}\n\n"

    try:
        explanation = await generate_spanish_explanation(
            client=gemini_client,
            query=query,
            context=full_context_text,
            user_level=current_user.current_level,
            lang=lang
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Service Error: {str(e)}")

    first_chunk_id = context_data['ids'][0][0]

    result = await db.execute(
        select(Progress).where(
            Progress.user_id == current_user.id, Progress.chunk_id == first_chunk_id
        )
    )

    if not result.scalar_one_or_none():
        new_progress = Progress(
            user_id=current_user.id,
            chunk_id=first_chunk_id,
            status="learning"
        )
        db.add(new_progress)
        await db.commit()

    return {
        "explanation": explanation,
        "source_chunks": context_data['ids'],
        "context_used": full_context_text[:300] + "..."
    }


@router.get("/topics", response_model=List[TopicSchema])
async def get_topics(
    lang: str = "en",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_guest)
):
    """Returns a list of topics and subtopics available for the user's current level."""
    user_level = current_user.current_level

    result = await db.execute(
        select(
            RuleExplanation.topic,
            RuleExplanation.subtopic,
            RuleExplanation.chunk_id,
            RuleExplanation.display_title
        ).where(
            RuleExplanation.lang == lang,
            RuleExplanation.level == user_level
        ).distinct()
        .order_by(RuleExplanation.topic, RuleExplanation.subtopic, RuleExplanation.chunk_id)
    )
    all_rules_data = result.all()

    topics_map = {}
    for topic, subtopic, chunk_id, display_title in all_rules_data:
        if topic not in topics_map:
            topics_map[topic] = {"first_chunk_id": chunk_id, "subtopics": {}}
        if subtopic not in topics_map[topic]["subtopics"]:
            topics_map[topic]["subtopics"][subtopic] = []
        topics_map[topic]["subtopics"][subtopic].append(
            RuleListItemSchema(chunk_id=chunk_id, display_title=display_title)
        )

    response_topics: List[TopicSchema] = []
    for topic_name, topic_data in topics_map.items():
        subtopics_map = topic_data["subtopics"]

        subtopics_list: List[SubtopicSchema] = []
        for subtopic_name, rules_list_items in subtopics_map.items():
            rules_list_items.sort(key=lambda x: parse_chunk_id_for_sort(x.chunk_id))
            first_chunk_id_for_subtopic = rules_list_items[0].chunk_id if rules_list_items else ""
            subtopics_list.append(
                SubtopicSchema(
                    name=subtopic_name,
                    rules=rules_list_items,
                    first_chunk_id=first_chunk_id_for_subtopic
                )
            )

        subtopics_list.sort(key=lambda x: parse_chunk_id_for_sort(x.first_chunk_id))
        response_topics.append(TopicSchema(name=topic_name, subtopics=subtopics_list))

    response_topics.sort(key=lambda x: parse_chunk_id_for_sort(topics_map[x.name]["first_chunk_id"]))

    return response_topics


@router.get("/chat_history", response_model=ChatHistoryResponse)
async def get_chat_history(
    current_user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves chat history for the authenticated user."""
    chat_session_query = await db.execute(
        select(ChatSession).where(ChatSession.user_id == current_user.id)
    )
    chat_session = chat_session_query.scalar_one_or_none()

    if not chat_session:
        return ChatHistoryResponse(history=[])

    history_schemas = []
    if chat_session and chat_session.history:
        for msg_dict in chat_session.history:
            try:
                history_schemas.append(
                    ChatMessageSchema(
                        id=msg_dict.get('id'),
                        sender=msg_dict.get('sender'),
                        text=msg_dict.get('text'),
                        source_rules=msg_dict.get('source_rules')
                    )
                )
            except Exception as e:
                print(f"Error parsing chat message from history: {e}, message: {msg_dict}")
                continue

    return ChatHistoryResponse(history=history_schemas)


@router.post("/chatbot_query")
async def chatbot_query(
    data: ChatbotQueryRequest,
    request: Request,
    current_user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db)
):
    """Handles streaming chatbot queries using RAG context and Gemini LLM."""
    embedding_model = request.app.state.embedding_model
    collection = request.app.state.collection
    gemini_client = request.app.state.gemini_client

    context_data = await get_extended_context(
        query_text=data.query,
        collection=collection,
        model=embedding_model,
        user_level=current_user.current_level,
        n_results=30
    )

    if not context_data or not context_data['documents'] or not context_data['documents'][0]:
        raise HTTPException(
            status_code=404,
            detail="Sorry, I could not find relevant information in the knowledge base for your query."
        )

    full_context_text = ""
    source_chunk_ids = []
    for cid, doc in zip(context_data['ids'][0], context_data['documents'][0]):
        full_context_text += f"--- Chunk ID: {cid} ---\n{doc}\n\n"
        source_chunk_ids.append(cid)

    rag_source_rules_for_llm: List[RuleListItemSchema] = []
    if source_chunk_ids:
        rules_query = await db.execute(
            select(RuleExplanation.chunk_id, RuleExplanation.display_title)
            .where(
                RuleExplanation.chunk_id.in_(source_chunk_ids),
                RuleExplanation.level == current_user.current_level,
                RuleExplanation.lang == data.lang
            )
            .distinct()
        )
        for r_chunk_id, r_display_title in rules_query.all():
            rag_source_rules_for_llm.append(
                RuleListItemSchema(chunk_id=r_chunk_id, display_title=r_display_title)
            )

    rag_source_rules_for_llm.sort(key=lambda x: parse_chunk_id_for_sort(x.chunk_id))

    async def generate_and_stream():
        full_llm_response_text = ""
        llm_suggested_rule_titles = []
        AsyncSessionLocal = get_db_session_factory()

        try:
            async for payload in generate_chatbot_answer(
                client=gemini_client,
                query=data.query,
                context=full_context_text,
                user_level=current_user.current_level,
                lang=data.lang,
                source_rules=rag_source_rules_for_llm
            ):
                if payload["type"] == "text":
                    yield f"data: {json.dumps(payload)}\n\n"
                    full_llm_response_text += payload["content"]
                elif payload["type"] == "final":
                    llm_suggested_rule_titles = payload["relevant_rule_titles"]
                elif payload["type"] == "error":
                    yield f"data: {json.dumps(payload)}\n\n"
                    return

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Streaming error: {str(e)}'})}\n\n"
            return

        final_source_rules: List[RuleListItemSchema] = []
        if llm_suggested_rule_titles:
            async with AsyncSessionLocal() as session_for_db:
                matched_rules_query = await session_for_db.execute(
                    select(RuleExplanation.chunk_id, RuleExplanation.display_title)
                    .where(
                        RuleExplanation.display_title.in_(llm_suggested_rule_titles),
                        RuleExplanation.level == current_user.current_level,
                        RuleExplanation.lang == data.lang
                    )
                    .distinct()
                )
                for r_chunk_id, r_display_title in matched_rules_query.all():
                    final_source_rules.append(
                        RuleListItemSchema(chunk_id=r_chunk_id, display_title=r_display_title)
                    )

        final_source_rules.sort(key=lambda x: parse_chunk_id_for_sort(x.chunk_id))

        user_msg_id = None
        bot_msg_id = None

        if current_user.id != 0:
            async with AsyncSessionLocal() as session_for_db:
                chat_session_query = await session_for_db.execute(
                    select(ChatSession).where(ChatSession.user_id == current_user.id)
                )
                chat_session = chat_session_query.scalar_one_or_none()

                if not chat_session:
                    chat_session = ChatSession(user_id=current_user.id, history=[])
                    session_for_db.add(chat_session)
                    await session_for_db.flush()

                user_msg_id = len(chat_session.history) + 1
                bot_msg_id = len(chat_session.history) + 2

                user_msg = ChatMessageSchema(id=user_msg_id, sender="user", text=data.query)
                bot_msg = ChatMessageSchema(
                    id=bot_msg_id,
                    sender="bot",
                    text=full_llm_response_text,
                    source_rules=final_source_rules
                )

                chat_session.history.append(user_msg.model_dump())
                chat_session.history.append(bot_msg.model_dump())

                await session_for_db.commit()

        yield f"data: {json.dumps({'type': 'final', 'user_message_id': user_msg_id, 'bot_message_id': bot_msg_id, 'source_rules': [sr.model_dump() for sr in final_source_rules]})}\n\n"

    return StreamingResponse(generate_and_stream(), media_type="text/event-stream")


@router.post("/chat_feedback", status_code=status.HTTP_204_NO_CONTENT)
async def chat_feedback(
    data: ChatFeedbackRequest,
    current_user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    """Records user feedback for a chat message."""
    if current_user.id == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest users cannot provide feedback."
        )

    chat_session_query = await db.execute(
        select(ChatSession).where(ChatSession.user_id == current_user.id)
    )
    chat_session = chat_session_query.scalar_one_or_none()

    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found for user.")

    query_text = ""
    bot_answer_text = ""
    found_message = None
    for i, msg_dict in enumerate(chat_session.history):
        if msg_dict.get('id') == data.message_id:
            found_message = msg_dict
            if i > 0 and chat_session.history[i - 1].get('sender') == 'user':
                query_text = chat_session.history[i - 1].get('text', '')
            bot_answer_text = msg_dict.get('text', '')
            break

    if not found_message:
        raise HTTPException(status_code=404, detail="Message not found in chat history.")

    new_feedback = ChatFeedback(
        user_id=current_user.id,
        chat_session_id=chat_session.id,
        message_id=data.message_id,
        query_text=query_text,
        bot_answer_text=bot_answer_text,
        feedback_type=data.feedback_type
    )
    db.add(new_feedback)
    await db.commit()


@router.get("/chat_feedback_for_session", response_model=List[ChatFeedbackItemSchema])
async def get_chat_feedback_for_session(
    current_user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all feedback submitted for the user's active chat session."""
    if current_user.id == 0:
        return []

    chat_session_query = await db.execute(
        select(ChatSession).where(ChatSession.user_id == current_user.id)
    )
    chat_session = chat_session_query.scalar_one_or_none()

    if not chat_session:
        return []

    feedback_query = await db.execute(
        select(ChatFeedback).where(ChatFeedback.chat_session_id == chat_session.id)
    )
    feedback_items = feedback_query.scalars().all()

    return [ChatFeedbackItemSchema.from_orm(item) for item in feedback_items]


@router.post("/generate_additional_exercises", response_model=GenerateAdditionalExercisesResponse)
async def generate_additional_exercises_endpoint(
    data: GenerateAdditionalExercisesRequest,
    request: Request,
    current_user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db)
):
    """Generates additional exercises for a specific rule using Gemini LLM."""
    embedding_model = request.app.state.embedding_model
    collection = request.app.state.collection
    gemini_client = request.app.state.gemini_client

    context_data = await get_extended_context(
        query_text=data.chunk_id,
        collection=collection,
        model=embedding_model,
        user_level=current_user.current_level,
        n_results=1
    )

    if not context_data or not context_data['documents'] or not context_data['documents'][0]:
        raise HTTPException(status_code=404, detail=f"Context for rule {data.chunk_id} not found.")

    rule_context_text = context_data['documents'][0][0]

    try:
        generated_exercises_data = await generate_additional_exercises(
            client=gemini_client,
            rule_context=rule_context_text,
            target_level=current_user.current_level,
            lang=data.lang,
            exercise_type=data.exercise_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM Service Error during additional exercise generation: {str(e)}"
        )

    exercises_with_temp_ids: List[Any] = []
    for i, ex in enumerate(generated_exercises_data):
        exercises_with_temp_ids.append({**ex, "id": -(i + 1)})

    return GenerateAdditionalExercisesResponse(exercises=exercises_with_temp_ids)


@router.get("/{chunk_id}", response_model=RuleExplanationResponse)
async def get_rule(
    chunk_id: str,
    lang: str = "en",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_guest)
):
    """Retrieves full rule explanation, related exercises, and the next rule chunk ID."""
    result = await db.execute(
        select(RuleExplanation).options(selectinload(RuleExplanation.exercises_rel)).where(
            RuleExplanation.chunk_id == chunk_id,
            RuleExplanation.lang == lang,
            RuleExplanation.level == current_user.current_level
        )
    )
    explanation = result.scalar_one_or_none()

    if not explanation:
        raise HTTPException(
            status_code=404,
            detail=f"Explanation for rule {chunk_id} at level {current_user.current_level} not found"
        )

    next_id_result = await db.execute(
        select(RuleExplanation.chunk_id).where(
            RuleExplanation.lang == lang,
            RuleExplanation.level == current_user.current_level
        ).distinct()
    )
    all_chunks = [r[0] for r in next_id_result.all()]
    all_chunks.sort(key=parse_chunk_id_for_sort)

    next_chunk_id = None
    try:
        current_index = all_chunks.index(chunk_id)
        if current_index + 1 < len(all_chunks):
            next_chunk_id = all_chunks[current_index + 1]
    except ValueError:
        pass

    response_data = RuleExplanationResponse.from_orm(explanation)
    response_data.next_chunk_id = next_chunk_id

    return response_data
