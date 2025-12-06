from typing import List,Optional
from pydantic import BaseModel,Field, field_validator

class TeamMember(BaseModel):
    """
    Represents one team member in the system.
    Used later for task assignment.
    """
    name: str = Field(..., min_length=1)
    role: str
    skills: List[str]


class Team(BaseModel):
    """
    Represents the full team.
    """
    members : List[TeamMember]

    @field_validator("members")
    def at_least_one_member(cls, v: List[TeamMember]) -> List[TeamMember]:
        if not v:
            raise ValueError("Team must have at least one member")
        return v