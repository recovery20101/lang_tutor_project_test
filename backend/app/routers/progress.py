import math
import re
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Progress, RuleExplanation, User
from app.schemas.progress import (
    ProgressDashboardResponse,
    ReviewItemSchema,
    TopicProgressSchema,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/progress", tags=["progress"])


def parse_chunk_id_for_sort(chunk_id: str) -> List[int]:
    """Extracts numeric indices from a chunk ID for natural sorting."""
    numbers = re.findall(r'\d+', chunk_id)
    return [int(n) for n in numbers]


@router.get("", response_model=ProgressDashboardResponse)
async def get_user_progress_dashboard(
    lang: str = "en",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves the user progress dashboard including topic completion and SM-2 review queues."""
    user_level = current_user.current_level
    user_id = current_user.id
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 1. Total unique chunk IDs per topic
    total_rules_stmt = (
        select(RuleExplanation.topic, func.count(distinct(RuleExplanation.chunk_id)))
        .where(
            RuleExplanation.lang == lang,
            RuleExplanation.level == user_level
        )
        .group_by(RuleExplanation.topic)
    )
    total_rules_result = await db.execute(total_rules_stmt)
    total_rules_map = {topic: count for topic, count in total_rules_result.all()}

    # 2. Count completed/read rules per topic
    completed_rules_stmt = (
        select(RuleExplanation.topic, func.count(distinct(Progress.chunk_id)))
        .join(Progress, Progress.chunk_id == RuleExplanation.chunk_id)
        .where(
            Progress.user_id == user_id,
            Progress.status.in_(["mastered", "read"]),
            RuleExplanation.lang == lang,
            RuleExplanation.level == user_level
        )
        .group_by(RuleExplanation.topic)
    )
    completed_rules_result = await db.execute(completed_rules_stmt)
    completed_rules_map = {topic: count for topic, count in completed_rules_result.all()}

    topics_progress: List[TopicProgressSchema] = []
    for topic_name, total_count in total_rules_map.items():
        completed_count = completed_rules_map.get(topic_name, 0)
        topics_progress.append(
            TopicProgressSchema(
                name=topic_name,
                completed_count=completed_count,
                total_count=total_count
            )
        )

    topics_progress.sort(key=lambda x: parse_chunk_id_for_sort(x.name))

    # 3. SM-2 review queue
    reviews_stmt = (
        select(
            Progress.chunk_id,
            Progress.next_review,
            RuleExplanation.display_title
        )
        .join(RuleExplanation, RuleExplanation.chunk_id == Progress.chunk_id)
        .where(
            Progress.user_id == user_id,
            Progress.status == "mastered",
            Progress.next_review <= now,
            RuleExplanation.lang == lang,
            RuleExplanation.level == user_level
        )
        .group_by(Progress.chunk_id, Progress.next_review, RuleExplanation.display_title)
    )
    reviews_result = await db.execute(reviews_stmt)

    review_items: List[ReviewItemSchema] = []
    for chunk_id, next_review, display_title in reviews_result.all():
        overdue_days = 0
        if next_review:
            delta = now - next_review
            delta_seconds = delta.total_seconds()
            if delta_seconds > 0:
                overdue_days = math.ceil(delta_seconds / 86400)

        review_items.append(
            ReviewItemSchema(
                chunk_id=chunk_id,
                display_title=display_title,
                overdue_days=overdue_days
            )
        )

    review_items.sort(key=lambda x: (x.overdue_days, parse_chunk_id_for_sort(x.chunk_id)), reverse=True)

    return ProgressDashboardResponse(
        topics=topics_progress,
        reviews=review_items
    )
