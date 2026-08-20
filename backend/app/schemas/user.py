from pydantic import BaseModel


class UpdateUserLevelRequest(BaseModel):
    """Schema for updating the user's proficiency level."""

    level: str
