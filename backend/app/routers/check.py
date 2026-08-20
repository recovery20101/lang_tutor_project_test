from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Exercise, Progress, User
from app.schemas.check import CheckRequest, ReadOverviewRequest
from app.schemas.rules import CheckDynamicExerciseRequest
from app.services.auth import get_current_user
from app.services.llm import verify_user_answer
from app.services.rag import get_extended_context
from app.services.sm2 import calculate_sm2

router = APIRouter(prefix="/check", tags=["assessment"])


@router.post("")
async def check_answer(
    data: CheckRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verifies a user answer for a specific exercise and updates SM-2 progress metrics."""
    embedding_model = request.app.state.embedding_model
    collection = request.app.state.collection
    gemini_client = request.app.state.gemini_client

    exercise_query = await db.execute(
        select(Exercise).where(Exercise.id == data.exercise_id)
    )
    exercise_obj: Optional[Exercise] = exercise_query.scalar_one_or_none()

    if not exercise_obj:
        raise HTTPException(status_code=404, detail="Exercise not found.")

    context_data = await get_extended_context(
        query_text=data.chunk_id,
        collection=collection,
        model=embedding_model,
        user_level=current_user.current_level,
        n_results=1
    )

    if not context_data or not context_data['documents'] or not context_data['documents'][0]:
        raise HTTPException(status_code=404, detail="Rule not found or context is empty.")

    full_context_text = "\n\n---\n\n".join(context_data['documents'][0])

    try:
        assessment = await verify_user_answer(
            client=gemini_client,
            rule_context=full_context_text,
            user_answer=data.user_answer,
            exercise_type=exercise_obj.type,
            original_question=exercise_obj.question,
            correct_answer_example=exercise_obj.correct_answer,
            lang=data.lang
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")

    gemini_score = assessment.get("score", 0)

    stmt = select(Progress).where(
        Progress.user_id == current_user.id,
        Progress.chunk_id == data.chunk_id
    )
    result = await db.execute(stmt)
    progress_entry = result.scalar_one_or_none()

    if progress_entry:
        sm2_updates = calculate_sm2(
            score_10=gemini_score,
            repetitions=progress_entry.repetitions,
            interval=progress_entry.interval,
            easiness_factor=progress_entry.easiness_factor
        )

        progress_entry.repetitions = sm2_updates["repetitions"]
        progress_entry.interval = sm2_updates["interval"]
        progress_entry.easiness_factor = sm2_updates["easiness_factor"]
        progress_entry.last_reviewed = sm2_updates["last_reviewed"]
        progress_entry.next_review = sm2_updates["next_review"]
        progress_entry.status = sm2_updates["status"]
    else:
        sm2_updates = calculate_sm2(
            score_10=gemini_score,
            repetitions=0,
            interval=1,
            easiness_factor=2.5
        )

        new_progress = Progress(
            user_id=current_user.id,
            chunk_id=data.chunk_id,
            repetitions=sm2_updates["repetitions"],
            interval=sm2_updates["interval"],
            easiness_factor=sm2_updates["easiness_factor"],
            last_reviewed=sm2_updates["last_reviewed"],
            next_review=sm2_updates["next_review"],
            status=sm2_updates["status"]
        )
        db.add(new_progress)

    await db.commit()

    assessment["sm2_stats"] = {
        "interval": sm2_updates["interval"],
        "easiness_factor": sm2_updates["easiness_factor"],
        "next_review": sm2_updates["next_review"].isoformat()
    }

    return assessment


@router.post("/dynamic_exercise")
async def check_dynamic_exercise(
    data: CheckDynamicExerciseRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verifies a user answer for a dynamically generated exercise without saving progress."""
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
        raise HTTPException(status_code=404, detail="Rule not found or context is empty.")

    full_context_text = "\n\n---\n\n".join(context_data['documents'][0])

    try:
        assessment = await verify_user_answer(
            client=gemini_client,
            rule_context=full_context_text,
            user_answer=data.user_answer,
            exercise_type=data.exercise_type,
            original_question=data.original_question,
            correct_answer_example=data.correct_answer_example,
            lang=data.lang
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")

    return assessment


@router.post("/overview/read")
async def mark_overview_as_read(
    data: ReadOverviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Marks an educational overview/rule section as read by the user."""
    stmt = select(Progress).where(
        Progress.user_id == current_user.id,
        Progress.chunk_id == data.chunk_id
    )
    result = await db.execute(stmt)
    progress_entry = result.scalar_one_or_none()

    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

    if progress_entry:
        progress_entry.last_reviewed = now_naive
        if progress_entry.status != "mastered":
            progress_entry.status = "read"
    else:
        new_progress = Progress(
            user_id=current_user.id,
            chunk_id=data.chunk_id,
            status="read",
            last_reviewed=now_naive,
            repetitions=0,
            interval=1,
            easiness_factor=2.5
        )
        db.add(new_progress)

    await db.commit()
    return {"status": "success", "message": "Overview marked as read"}
