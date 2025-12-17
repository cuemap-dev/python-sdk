"""
CueMap: Redis for AI Agents

A high-performance, temporal-associative memory store.
You give us the cues, we give you the right memory at the right time.

Example:
    >>> from cuemap import CueMap
    >>> 
    >>> client = CueMap()
    >>> 
    >>> # Add a memory with cues
    >>> client.add("The server password is abc123", cues=["server", "password"])
    >>> 
    >>> # Recall by cues
    >>> results = client.recall(["server", "password"])
    >>> print(results[0].content)
"""

from .client import CueMap, AsyncCueMap
from .models import Memory, RecallResult
from .exceptions import CueMapError, ConnectionError, AuthenticationError

__version__ = "0.2.0"
__all__ = [
    "CueMap",
    "AsyncCueMap",
    "Memory",
    "RecallResult",
    "CueMapError",
    "ConnectionError",
    "AuthenticationError",
]
