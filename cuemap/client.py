"""Pure CueMap client - no magic, just speed."""

import httpx
from typing import List, Optional, Dict, Any

from .models import Memory, RecallResult
from .exceptions import CueMapError, ConnectionError, AuthenticationError


class CueMap:
    """
    Pure CueMap client.
    
    No auto-cue extraction. No semantic matching. Just fast memory storage.
    
    Example:
        >>> client = CueMap()
        >>> client.add("Important note", cues=["work", "urgent"])
        >>> results = client.recall(["work"])
    """
    
    def __init__(
        self,
        url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize CueMap client.
        
        Args:
            url: CueMap server URL
            api_key: Optional API key for authentication
            project_id: Optional project ID for multi-tenancy
            timeout: Request timeout in seconds
        """
        self.url = url
        self.api_key = api_key
        self.project_id = project_id
        
        self.client = httpx.Client(
            base_url=url,
            timeout=timeout
        )
    
    def _headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if self.project_id:
            headers["X-Project-ID"] = self.project_id
        return headers
    
    def add(
        self,
        content: str,
        cues: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a memory.
        
        Args:
            content: Memory content
            cues: List of cues (tags) for retrieval
            metadata: Optional metadata
            
        Returns:
            Memory ID
            
        Example:
            >>> client.add(
            ...     "Meeting with John at 3pm",
            ...     cues=["meeting", "john", "calendar"]
            ... )
        """
        response = self.client.post(
            "/memories",
            json={
                "content": content,
                "cues": cues,
                "metadata": metadata or {}
            },
            headers=self._headers()
        )
        
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code != 200:
            raise CueMapError(f"Failed to add memory: {response.status_code}")
        
        return response.json()["id"]
    
    def recall(
        self,
        cues: List[str],
        limit: int = 10,
        auto_reinforce: bool = False,
        min_intersection: Optional[int] = None,
        projects: Optional[List[str]] = None
    ) -> List[RecallResult]:
        """
        Recall memories by cues.
        
        Args:
            cues: List of cues to search for
            limit: Maximum results to return
            auto_reinforce: Automatically reinforce retrieved memories
            min_intersection: Minimum number of cues that must match (for strict AND logic)
            projects: List of project IDs for cross-domain queries (multi-tenant only)
            
        Returns:
            List of recall results
            
        Example:
            >>> # OR logic (default): matches any cue
            >>> results = client.recall(["meeting", "john"])
            
            >>> # AND logic: requires both cues
            >>> results = client.recall(["meeting", "john"], min_intersection=2)
            
            >>> # Cross-domain query (multi-tenant)
            >>> results = client.recall(["urgent"], projects=["sales", "support"])
        """
        payload = {
            "cues": cues,
            "limit": limit,
            "auto_reinforce": auto_reinforce
        }
        
        if min_intersection is not None:
            payload["min_intersection"] = min_intersection
        
        if projects is not None:
            payload["projects"] = projects
        
        response = self.client.post(
            "/recall",
            json=payload,
            headers=self._headers()
        )
        
        if response.status_code != 200:
            raise CueMapError(f"Failed to recall: {response.status_code}")
        
        results = response.json()["results"]
        return [RecallResult(**r) for r in results]
    
    def reinforce(self, memory_id: str, cues: List[str]) -> bool:
        """
        Reinforce a memory on specific cue pathways.
        
        Args:
            memory_id: Memory ID
            cues: Cues to reinforce on
            
        Returns:
            Success status
        """
        response = self.client.patch(
            f"/memories/{memory_id}/reinforce",
            json={"cues": cues},
            headers=self._headers()
        )
        
        return response.status_code == 200
    
    def get(self, memory_id: str) -> Memory:
        """Get a memory by ID."""
        response = self.client.get(
            f"/memories/{memory_id}",
            headers=self._headers()
        )
        
        if response.status_code == 404:
            raise CueMapError(f"Memory not found: {memory_id}")
        elif response.status_code != 200:
            raise CueMapError(f"Failed to get memory: {response.status_code}")
        
        return Memory(**response.json())
    
    def stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        response = self.client.get(
            "/stats",
            headers=self._headers()
        )
        
        return response.json()
    
    def close(self):
        """Close the client."""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AsyncCueMap:
    """
    Async CueMap client.
    
    Example:
        >>> async with AsyncCueMap() as client:
        ...     await client.add("Note", cues=["work"])
        ...     results = await client.recall(["work"])
    """
    
    def __init__(
        self,
        url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        timeout: float = 30.0
    ):
        self.url = url
        self.api_key = api_key
        self.project_id = project_id
        
        self.client = httpx.AsyncClient(
            base_url=url,
            timeout=timeout
        )
    
    def _headers(self) -> Dict[str, str]:
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if self.project_id:
            headers["X-Project-ID"] = self.project_id
        return headers
    
    async def add(
        self,
        content: str,
        cues: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a memory (async)."""
        response = await self.client.post(
            "/memories",
            json={
                "content": content,
                "cues": cues,
                "metadata": metadata or {}
            },
            headers=self._headers()
        )
        
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code != 200:
            raise CueMapError(f"Failed to add memory: {response.status_code}")
        
        return response.json()["id"]
    
    async def recall(
        self,
        cues: List[str],
        limit: int = 10,
        auto_reinforce: bool = False,
        min_intersection: Optional[int] = None,
        projects: Optional[List[str]] = None
    ) -> List[RecallResult]:
        """Recall memories (async)."""
        payload = {
            "cues": cues,
            "limit": limit,
            "auto_reinforce": auto_reinforce
        }
        
        if min_intersection is not None:
            payload["min_intersection"] = min_intersection
        
        if projects is not None:
            payload["projects"] = projects
        
        response = await self.client.post(
            "/recall",
            json=payload,
            headers=self._headers()
        )
        
        if response.status_code != 200:
            raise CueMapError(f"Failed to recall: {response.status_code}")
        
        results = response.json()["results"]
        return [RecallResult(**r) for r in results]
    
    async def reinforce(self, memory_id: str, cues: List[str]) -> bool:
        """Reinforce a memory (async)."""
        response = await self.client.patch(
            f"/memories/{memory_id}/reinforce",
            json={"cues": cues},
            headers=self._headers()
        )
        
        return response.status_code == 200
    
    async def get(self, memory_id: str) -> Memory:
        """Get a memory by ID (async)."""
        response = await self.client.get(
            f"/memories/{memory_id}",
            headers=self._headers()
        )
        
        if response.status_code == 404:
            raise CueMapError(f"Memory not found: {memory_id}")
        elif response.status_code != 200:
            raise CueMapError(f"Failed to get memory: {response.status_code}")
        
        return Memory(**response.json())
    
    async def stats(self) -> Dict[str, Any]:
        """Get server statistics (async)."""
        response = await self.client.get(
            "/stats",
            headers=self._headers()
        )
        
        return response.json()
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
