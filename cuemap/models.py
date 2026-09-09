"""Data models."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

MemoryId = Union[int, str]


class Memory(BaseModel):
    """A memory object."""
    
    id: MemoryId
    content: Union[str, List[int]]
    source_key: Optional[str] = None
    cues: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[float] = None
    last_accessed: Optional[float] = None
    disk_backed: bool = False
    scoring_features: Dict[str, Any] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)


class RecallResult(BaseModel):
    """Result from a recall operation."""
    
    memory_id: MemoryId
    content: str
    score: float
    intersection_count: int
    recency_score: float
    reinforcement_score: float
    salience_score: float = 0.0
    salience: float = 0.0
    match_integrity: float = 0.0
    created_at: Optional[float] = None
    structural_cues: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    explain: Optional[Dict[str, Any]] = None


class RecallPreviewResult(RecallResult):
    """Engine-provided leading excerpt; fetch the memory for full evidence."""
    content: Optional[str] = None
    preview: str
    content_truncated: bool
    content_length: int
