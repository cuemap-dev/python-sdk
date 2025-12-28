"""Data models."""

from typing import Dict, List, Any, Optional
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
    salience: float = 0.0
    match_integrity: float = 0.0
    structural_cues: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    explain: Optional[Dict[str, Any]] = None
