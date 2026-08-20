from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Represents a registered user in the database."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    current_level: Mapped[str] = mapped_column(String(2), default="A1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    progress: Mapped[list["Progress"]] = relationship(back_populates="user_obj")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user")
    feedback: Mapped[list["ChatFeedback"]] = relationship(back_populates="user")


class Progress(Base):
    """Represents user progress and spaced repetition metrics for rule chunks."""

    __tablename__ = "user_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    chunk_id: Mapped[str] = mapped_column(String(50), index=True)

    status: Mapped[str] = mapped_column(String(20), default="new")
    last_reviewed: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    next_review: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    easiness_factor: Mapped[float] = mapped_column(default=2.5)
    interval: Mapped[int] = mapped_column(default=0)
    repetitions: Mapped[int] = mapped_column(default=0)

    user_obj: Mapped["User"] = relationship(back_populates="progress")


class ChatSession(Base):
    """Represents an active or stored chat session for a user."""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    history: Mapped[list[dict]] = mapped_column(MutableList.as_mutable(JSON), default=list)

    user: Mapped["User"] = relationship(back_populates="chat_sessions")
    feedback: Mapped[list["ChatFeedback"]] = relationship(back_populates="chat_session")


class ChatFeedback(Base):
    """Represents user feedback on chat responses."""

    __tablename__ = "chat_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    chat_session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"))
    message_id: Mapped[int] = mapped_column()
    query_text: Mapped[str] = mapped_column(Text)
    bot_answer_text: Mapped[str] = mapped_column(Text)
    feedback_type: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="feedback")
    chat_session: Mapped["ChatSession"] = relationship(back_populates="feedback")


class RuleExplanation(Base):
    """Represents generated rule explanations for specific proficiency levels and languages."""

    __tablename__ = "rule_explanations"

    id: Mapped[int] = mapped_column(primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(50), index=True)
    level: Mapped[str] = mapped_column(String(2))
    lang: Mapped[str] = mapped_column(String(5))
    topic: Mapped[str] = mapped_column(String(100))
    subtopic: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    display_title: Mapped[str] = mapped_column(String, nullable=True)
    related_rules: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    exercises_rel: Mapped[List["Exercise"]] = relationship(back_populates="rule_explanation")

    __table_args__ = (
        UniqueConstraint('chunk_id', 'level', 'lang', name='_chunk_level_lang_uc'),
    )


class Exercise(Base):
    """Represents practice exercises linked to rule explanations."""

    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_explanation_id: Mapped[int] = mapped_column(ForeignKey("rule_explanations.id"))

    type: Mapped[str] = mapped_column(String(50))
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text)
    translation: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    rule_explanation: Mapped["RuleExplanation"] = relationship(back_populates="exercises_rel")
