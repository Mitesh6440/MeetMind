from typing import List, Optional
from pydantic import BaseModel, Field


class Task(BaseModel):
    """
    Minimal Task model for matching & assignment.
    More fields (priority, deadline, etc.) can be added later.
    """
    id: int
    description: str = Field(..., min_length=3)

    # Filled by skill-matching step:
    required_skills: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    # Will be filled later by assignment logic:
    assigned_to: Optional[str] = None
