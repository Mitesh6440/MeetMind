from typing import Optional
from enum import Enum
from pydantic import BaseModel


class EntityType(str, Enum):
    PERSON = "person"
    TECHNICAL = "technical"
    TIME = "time"


class Entity(BaseModel):
    text: str
    type: EntityType
    start_char: Optional[int] = None
    end_char: Optional[int] = None
