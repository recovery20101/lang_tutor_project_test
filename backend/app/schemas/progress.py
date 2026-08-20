from typing import List, Optional
from pydantic import BaseModel


class TopicProgressSchema(BaseModel):
    """Schema for individual topic progress summary."""

    name: str
    completed_count: int
    total_count: int


class ReviewItemSchema(BaseModel):
    """Schema for SM-2 review queue items."""

    chunk_id: str
    display_title: Optional[str] = None
    overdue_days: int


class ProgressDashboardResponse(BaseModel):
    """Schema for user progress dashboard response."""

    topics: List[TopicProgressSchema]
    reviews: List[ReviewItemSchema]
