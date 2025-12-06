from typing import List
from pydantic import BaseModel, Field


class PreprocessedSentence(BaseModel):
    """
    Represents one sentence after preprocessing.
    """
    id: int
    raw_text: str = Field(..., min_length=1)      # original sentence from transcript
    cleaned_text: str = Field(..., min_length=1)  # normalized, filler-removed sentence
    tokens: List[str] = Field(default_factory=list)
