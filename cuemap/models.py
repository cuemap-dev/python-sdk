"""Data models."""

from typing import Dict, List, Any
from pydantic import BaseModel, Field


class Memory(BaseModel):
    """A memory object."""
    
    id: str
    content: str
    cues: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecallResult(BaseModel):
    """Result from a recall operation."""
    
    memory_id: str
    content: str
    score: float
    intersection_count: int
    recency_score: float
    reinforcement_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
