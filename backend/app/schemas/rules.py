from typing import List, Optional, Union
from pydantic import BaseModel
from app.models import RuleExplanation


class RuleListItemSchema(BaseModel):
    """Schema for a rule summary item within lists or sidebars."""

    chunk_id: str
    display_title: Optional[str] = None


class SubtopicSchema(BaseModel):
    """Schema for grouping rules by subtopic."""

    name: str
    rules: List[RuleListItemSchema]
    first_chunk_id: str


class TopicSchema(BaseModel):
    """Schema for grouping subtopics under a main topic."""

    name: str
    subtopics: List[SubtopicSchema]


class FillInTheBlankExerciseSchema(BaseModel):
    """Schema for fill-in-the-blank exercises."""

    id: int
    type: str = "fill_in_the_blank"
    question: str
    correct_answer: str
    translation: str


class MultipleChoiceExerciseSchema(BaseModel):
    """Schema for multiple choice exercises."""

    id: int
    type: str = "multiple_choice"
    question: str
    options: List[str]
    correct_answer: str
    translation: str


class FreeResponseExerciseSchema(BaseModel):
    """Schema for free response exercises."""

    id: int
    type: str = "free_response"
    question: str
    correct_answer: str
    translation: str


ExerciseSchema = Union[
    FillInTheBlankExerciseSchema,
    MultipleChoiceExerciseSchema,
    FreeResponseExerciseSchema
]


class RuleExplanationResponse(BaseModel):
    """Schema for rule detail responses, including content and exercises."""

    chunk_id: str
    level: str
    lang: str
    topic: str
    subtopic: str
    content: str
    title: str
    display_title: Optional[str] = None
    related_rules: Optional[List[RuleListItemSchema]] = None
    next_chunk_id: Optional[str] = None
    exercises: Optional[List[ExerciseSchema]] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj: RuleExplanation):
        title = f"{obj.topic.replace('_', ' ').title()}"
        if obj.subtopic and obj.subtopic != obj.topic:
            title += f": {obj.subtopic.replace('_', ' ').title()}"

        exercises_list: List[ExerciseSchema] = []
        if obj.exercises_rel:
            for ex_obj in obj.exercises_rel:
                if ex_obj.type == "fill_in_the_blank":
                    exercises_list.append(FillInTheBlankExerciseSchema(
                        id=ex_obj.id,
                        question=ex_obj.question,
                        correct_answer=ex_obj.correct_answer,
                        translation=ex_obj.translation
                    ))
                elif ex_obj.type == "multiple_choice":
                    exercises_list.append(MultipleChoiceExerciseSchema(
                        id=ex_obj.id,
                        question=ex_obj.question,
                        options=ex_obj.options or [],
                        correct_answer=ex_obj.correct_answer,
                        translation=ex_obj.translation
                    ))
                elif ex_obj.type == "free_response":
                    exercises_list.append(FreeResponseExerciseSchema(
                        id=ex_obj.id,
                        question=ex_obj.question,
                        correct_answer=ex_obj.correct_answer,
                        translation=ex_obj.translation
                    ))

        return cls(
            chunk_id=obj.chunk_id,
            level=obj.level,
            lang=obj.lang,
            topic=obj.topic,
            subtopic=obj.subtopic,
            content=obj.content,
            title=title,
            display_title=obj.display_title,
            related_rules=obj.related_rules,
            exercises=exercises_list
        )


class ChatbotQueryRequest(BaseModel):
    """Schema for chatbot query requests."""

    query: str
    lang: str = "en"


class ChatbotResponse(BaseModel):
    """Schema for standard chatbot responses."""

    answer: str
    source_rules: List[RuleListItemSchema]


class ChatMessageSchema(BaseModel):
    """Schema for individual chat messages in history."""

    id: int
    sender: str
    text: str
    source_rules: Optional[List[RuleListItemSchema]] = None


class ChatHistoryResponse(BaseModel):
    """Schema for retrieving chat history."""

    history: List[ChatMessageSchema]


class SaveChatHistoryRequest(BaseModel):
    """Schema for saving chat history updates."""

    history: List[ChatMessageSchema]


class ChatFeedbackRequest(BaseModel):
    """Schema for submitting chat feedback."""

    message_id: int
    feedback_type: str


class ChatFeedbackItemSchema(BaseModel):
    """Schema for retrieving chat feedback items."""

    message_id: int
    feedback_type: str

    class Config:
        from_attributes = True


class GenerateAdditionalExercisesRequest(BaseModel):
    """Schema for requesting additional generated exercises."""

    chunk_id: str
    exercise_type: str
    lang: str = "en"


class GenerateAdditionalExercisesResponse(BaseModel):
    """Schema for responding with additional generated exercises."""

    exercises: List[ExerciseSchema]


class CheckDynamicExerciseRequest(BaseModel):
    """Schema for checking answers to dynamically generated exercises."""

    chunk_id: str
    user_answer: str
    exercise_type: str
    original_question: str
    correct_answer_example: str
    lang: str = "en"
