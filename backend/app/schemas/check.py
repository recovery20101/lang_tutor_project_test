from pydantic import BaseModel


class UserAnswerSchema(BaseModel):
    """Schema representing a user's answer submission for an exercise."""

    chunk_id: str
    exercise_id: int
    user_answer: str
    exercise_type: str


class AnswerFeedbackSchema(BaseModel):
    """Schema representing the feedback for a user's answer."""

    score: int
    correct_version: str
    explanation: str
    is_correct: bool


class CheckRequest(BaseModel):
    """Schema for checking a regular exercise answer."""

    chunk_id: str
    exercise_id: int
    user_answer: str
    lang: str = "en"


class ReadOverviewRequest(BaseModel):
    """Schema for marking a rule overview section as read."""

    chunk_id: str
