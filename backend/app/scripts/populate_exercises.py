import asyncio
from typing import Optional

import chromadb
from google.genai import Client
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Exercise, RuleExplanation
from app.services.llm import generate_exercises

LEVELS = ["A1", "A2", "B1", "B2"]
EXERCISE_CHUNK_TYPES = ["rule", "formation", "comparison", "usage_note"]
BATCH_SIZE_EXERCISES = settings.BATCH_SIZE_EXERCISES


async def get_chroma_client_and_collection():
    """Initializes and returns the ChromaDB client and collection."""
    chroma_host = settings.CHROMA_HOST
    chroma_port = settings.CHROMA_PORT
    print(f"Connecting to ChromaDB at {chroma_host}:{chroma_port}")
    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    collection = client.get_or_create_collection("spanish_grammar")
    print("ChromaDB collection 'spanish_grammar' initialized.")
    return client, collection


def get_db_session_factory():
    """Initializes and returns the SQLAlchemy session factory."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    print("SQLAlchemy engine and session factory initialized.")
    return AsyncSessionLocal


async def get_rule_context_from_chroma(collection, chunk_id: str) -> Optional[str]:
    """Retrieves original document text from ChromaDB by chunk ID."""
    main_chunk_results = collection.get(
        ids=[chunk_id],
        include=['documents']
    )
    if main_chunk_results['ids']:
        return main_chunk_results['documents'][0]
    return None


async def populate_exercises() -> None:
    """Populates the Exercise table with LLM-generated content."""
    print("Starting population of Exercise table with LLM-generated content...")

    chroma_client, collection = await get_chroma_client_and_collection()
    AsyncSessionLocal = get_db_session_factory()
    gemini_client = Client(api_key=settings.GEMINI_API_KEY)
    print("Gemini client initialized.")

    failed_generations = []
    max_retries = 3
    retry_delay_seconds = 5
    generated_count = 0

    async with AsyncSessionLocal() as session:
        rules_to_process_query = await session.execute(
            select(RuleExplanation)
        )
        all_rules_in_db = rules_to_process_query.scalars().all()

        rules_to_process = []
        for rule_explanation in all_rules_in_db:
            main_chunk_meta_results = collection.get(
                ids=[rule_explanation.chunk_id],
                include=['metadatas']
            )
            if not main_chunk_meta_results['ids']:
                print(f"Warning: Main chunk {rule_explanation.chunk_id} not found in ChromaDB.")
                continue

            chunk_type = main_chunk_meta_results['metadatas'][0].get('chunk_type')

            if chunk_type in EXERCISE_CHUNK_TYPES:
                existing_exercises_count = await session.scalar(
                    select(func.count(Exercise.id))
                    .where(Exercise.rule_explanation_id == rule_explanation.id)
                )
                if existing_exercises_count < 9:
                    rules_to_process.append(rule_explanation)
            else:
                print(f"Skipping exercise generation for {rule_explanation.chunk_id} (chunk_type: {chunk_type}).")

        print(f"Found {len(rules_to_process)} RuleExplanation entries to process for exercises.")

        for rule_explanation in rules_to_process:
            if generated_count >= BATCH_SIZE_EXERCISES:
                print(f"Batch size of {BATCH_SIZE_EXERCISES} reached for exercises. Stopping.")
                break

            chunk_id = rule_explanation.chunk_id
            target_level = rule_explanation.level

            print(f"Generating exercises for {chunk_id} at level {target_level}...")

            rule_context_text = await get_rule_context_from_chroma(collection, chunk_id)
            if not rule_context_text:
                print(f"Warning: No context found for {chunk_id}. Skipping.")
                continue

            try:
                exercises_data = await generate_exercises(
                    client=gemini_client,
                    rule_context=rule_context_text,
                    target_level=target_level,
                    lang="en",
                    rule_id=chunk_id
                )

                for ex_data in exercises_data:
                    new_exercise = Exercise(
                        rule_explanation_id=rule_explanation.id,
                        type=ex_data.get("type"),
                        question=ex_data.get("question", ex_data.get("sentence", ex_data.get("prompt"))),
                        options=ex_data.get("options"),
                        correct_answer=ex_data.get("correct_answer", ex_data.get("correct_answer_example")),
                        translation=ex_data.get("translation")
                    )
                    session.add(new_exercise)
                await session.commit()
                print(f"Added {len(exercises_data)} exercises for {chunk_id} at level {target_level}.")
                generated_count += 1

            except Exception as e:
                await session.rollback()
                print(f"Error generating exercises for {chunk_id} at level {target_level}: {e}.")
                failed_generations.append((chunk_id, target_level, 0))

            await asyncio.sleep(2)

    print("\n--- Starting retry loop for failed exercise generations ---")
    retries_queue = list(failed_generations)
    failed_generations.clear()

    for current_failed in retries_queue:
        if generated_count >= BATCH_SIZE_EXERCISES:
            print(f"Batch size of {BATCH_SIZE_EXERCISES} reached during retry. Stopping.")
            break

        chunk_id, target_level, retry_count = current_failed

        if retry_count >= max_retries:
            failed_generations.append((chunk_id, target_level, retry_count))
            continue

        async with AsyncSessionLocal() as session:
            rule_explanation_query = await session.execute(
                select(RuleExplanation).where(
                    RuleExplanation.chunk_id == chunk_id,
                    RuleExplanation.level == target_level,
                    RuleExplanation.lang == "en"
                )
            )
            rule_explanation = rule_explanation_query.scalar_one_or_none()

            if not rule_explanation:
                failed_generations.append((chunk_id, target_level, retry_count))
                continue

            rule_context_text = await get_rule_context_from_chroma(collection, chunk_id)
            if not rule_context_text:
                failed_generations.append((chunk_id, target_level, retry_count))
                continue

            try:
                exercises_data = await generate_exercises(
                    client=gemini_client,
                    rule_context=rule_context_text,
                    target_level=target_level,
                    lang="en",
                    rule_id=chunk_id
                )

                for ex_data in exercises_data:
                    new_exercise = Exercise(
                        rule_explanation_id=rule_explanation.id,
                        type=ex_data.get("type"),
                        question=ex_data.get("question", ex_data.get("sentence", ex_data.get("prompt"))),
                        options=ex_data.get("options"),
                        correct_answer=ex_data.get("correct_answer", ex_data.get("correct_answer_example")),
                        translation=ex_data.get("translation")
                    )
                    session.add(new_exercise)
                await session.commit()
                generated_count += 1

            except Exception as e:
                await session.rollback()
                failed_generations.append((chunk_id, target_level, retry_count + 1))

            await asyncio.sleep(retry_delay_seconds)

    print("\n--- Exercise table population complete. ---")


if __name__ == "__main__":
    asyncio.run(populate_exercises())
