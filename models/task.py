from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Import PriorityLevel for type hints (avoid circular import)
try:
    from src.services.priority_detection import PriorityLevel
except ImportError:
    # Fallback for when importing from models directly
    from enum import Enum
    class PriorityLevel(str, Enum):
        CRITICAL = "critical"
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"


class Task(BaseModel):
    """
    Task model for matching & assignment with priority and dependencies.
    """
    id: int
    description: str = Field(..., min_length=3)

    # Where this task came from in the transcript processing
    source_sentence_id: Optional[int] = None

    # Filled by skill-matching step:
    required_skills: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    # NER-related info 
    mentioned_people: List[str] = Field(default_factory=list)
    technical_terms: List[str] = Field(default_factory=list)
    time_expressions: List[str] = Field(default_factory=list)

    # Deadline extracted from temporal expressions
    deadline: Optional[datetime] = None

    # Priority level (Critical, High, Medium, Low)
    priority: Optional[str] = Field(default=None, description="Task priority: critical, high, medium, or low")

    # Dependencies: list of task IDs this task depends on
    dependencies: List[int] = Field(default_factory=list)

    # Will be filled later by assignment logic:
    assigned_to: Optional[str] = None
