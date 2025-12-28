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
        metadata: Optional[Dict[str, Any]] = None,
        disable_temporal_chunking: bool = False
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
                "metadata": metadata or {},
                "disable_temporal_chunking": disable_temporal_chunking
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
        cues: Optional[List[str]] = None,
        query_text: Optional[str] = None,
        limit: int = 10,
        auto_reinforce: bool = False,
        min_intersection: Optional[int] = None,
        projects: Optional[List[str]] = None,
        explain: bool = False,
        disable_pattern_completion: bool = False,
        disable_salience_bias: bool = False,
        disable_systems_consolidation: bool = False
    ) -> List[RecallResult]:
        """
        Recall memories by cues or natural language.
        
        Args:
            cues: List of cues to search for
            query_text: Natural language query to resolve via Lexicon
            limit: Maximum results to return
            auto_reinforce: Automatically reinforce retrieved memories
            min_intersection: Minimum number of cues that must match
            projects: List of project IDs for cross-domain queries
            explain: Include recall explanation in results
            
        Returns:
            List of recall results
            
        Example:
            >>> results = client.recall(query_text="payment failed", explain=True)
            >>> for r in results:
            ...     print(r.content, r.explain)
        """
        payload = {
            "limit": limit,
            "auto_reinforce": auto_reinforce,
            "explain": explain,
            "disable_pattern_completion": disable_pattern_completion,
            "disable_salience_bias": disable_salience_bias,
            "disable_systems_consolidation": disable_systems_consolidation
        }
        if cues:
            payload["cues"] = cues
        if query_text:
            payload["query_text"] = query_text
        if min_intersection is not None:
            payload["min_intersection"] = min_intersection
        if projects:
            payload["projects"] = projects

        response = self.client.post(
            "/recall",
            json=payload,
            headers=self._headers()
        )
        
        if response.status_code != 200:
            raise CueMapError(f"Failed to recall: {response.text}")
        
        data = response.json()
        results = data["results"]
        
        if projects and isinstance(results, list) and len(results) > 0 and "project_id" in results[0]:
            return data
            
        return [RecallResult(**r) for r in results]
    
    def recall_grounded(
        self,
        query: str,
        token_budget: int = 500,
        limit: int = 10,
        projects: Optional[List[str]] = None,
        disable_pattern_completion: bool = False,
        disable_salience_bias: bool = False,
        disable_systems_consolidation: bool = False
    ) -> Dict[str, Any]:
        """
        Recall grounded context with token budgeting.
        
        Returns a dictionary containing:
            - verified_context: The formatted context block string
            - proof: Detailed GroundingProof object
            - engine_latency_ms: Server-side latency
        """
        response = self.client.post(
            "/recall/grounded",
            json={
                "query_text": query,
                "token_budget": token_budget,
                "limit": limit,
                "projects": projects,
                "disable_pattern_completion": disable_pattern_completion,
                "disable_salience_bias": disable_salience_bias,
                "disable_systems_consolidation": disable_systems_consolidation
            },
            headers=self._headers()
        )
        
        if response.status_code != 200:
            raise CueMapError(f"Failed to recall grounded: {response.text}")
        
        return response.json()

    def list_projects(self) -> List[str]:
        """List all projects (multi-tenant only)."""
        response = self.client.get(
            "/projects",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to list projects: {response.text}")
        return response.json()

    def delete_project(self, project_id: str) -> bool:
        """Delete a project (multi-tenant only)."""
        response = self.client.delete(
            f"/projects/{project_id}",
            headers=self._headers()
        )
        return response.status_code == 200

    def add_alias(self, from_cue: str, to_cue: str, weight: float = 1.0) -> bool:
        """Add an alias (manual cue mapping)."""
        response = self.client.post(
            "/aliases",
            json={"from": from_cue, "to": to_cue, "weight": weight},
            headers=self._headers()
        )
        return response.status_code == 200

    def get_aliases(self, cue: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all aliases, optionally filtered by cue."""
        params = {}
        if cue:
            params["cue"] = cue
        response = self.client.get(
            "/aliases",
            params=params,
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to get aliases: {response.text}")
        return response.json()

    def merge_aliases(self, cues: List[str], to_cue: str) -> bool:
        """Merge multiple cues into a canonical canonical cue."""
        response = self.client.post(
            "/aliases/merge",
            json={"cues": cues, "to": to_cue},
            headers=self._headers()
        )
        return response.status_code == 200
    
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
                "metadata": metadata or {},
                "disable_temporal_chunking": disable_temporal_chunking
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
        cues: Optional[List[str]] = None,
        query_text: Optional[str] = None,
        limit: int = 10,
        auto_reinforce: bool = False,
        min_intersection: Optional[int] = None,
        projects: Optional[List[str]] = None,
        explain: bool = False,
        disable_pattern_completion: bool = False,
        disable_salience_bias: bool = False,
        disable_systems_consolidation: bool = False
    ) -> List[RecallResult]:
        """Recall memories (async)."""
        payload = {
            "limit": limit,
            "auto_reinforce": auto_reinforce,
            "explain": explain,
            "disable_pattern_completion": disable_pattern_completion,
            "disable_salience_bias": disable_salience_bias,
            "disable_systems_consolidation": disable_systems_consolidation
        }
        if cues:
            payload["cues"] = cues
        if query_text:
            payload["query_text"] = query_text
        if min_intersection is not None:
            payload["min_intersection"] = min_intersection
        if projects:
            payload["projects"] = projects

        response = await self.client.post(
            "/recall",
            json=payload,
            headers=self._headers()
        )
        
        if response.status_code != 200:
            raise CueMapError(f"Failed to recall: {response.status_code}")
        
        data = response.json()
        results = data["results"]
        
        if projects and isinstance(results, list) and len(results) > 0 and "project_id" in results[0]:
            return data
            
        return [RecallResult(**r) for r in results]
    
    async def recall_grounded(
        self,
        query: str,
        token_budget: int = 500,
        limit: int = 10,
        projects: Optional[List[str]] = None,
        disable_pattern_completion: bool = False,
        disable_salience_bias: bool = False,
        disable_systems_consolidation: bool = False
    ) -> Dict[str, Any]:
        """Recall grounded context (async)."""
        response = await self.client.post(
            "/recall/grounded",
            json={
                "query_text": query,
                "token_budget": token_budget,
                "limit": limit,
                "projects": projects,
                "disable_pattern_completion": disable_pattern_completion,
                "disable_salience_bias": disable_salience_bias,
                "disable_systems_consolidation": disable_systems_consolidation
            },
            headers=self._headers()
        )
        
        if response.status_code != 200:
            raise CueMapError(f"Failed to recall grounded: {response.text}")
        
        return response.json()

    async def list_projects(self) -> List[str]:
        """List all projects (async, multi-tenant only)."""
        response = await self.client.get(
            "/projects",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to list projects: {response.text}")
        return response.json()

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project (async, multi-tenant only)."""
        response = await self.client.delete(
            f"/projects/{project_id}",
            headers=self._headers()
        )
        return response.status_code == 200

    async def add_alias(self, from_cue: str, to_cue: str, weight: float = 1.0) -> bool:
        """Add an alias (async)."""
        response = await self.client.post(
            "/aliases",
            json={"from": from_cue, "to": to_cue, "weight": weight},
            headers=self._headers()
        )
        return response.status_code == 200

    async def get_aliases(self, cue: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get aliases (async)."""
        params = {}
        if cue:
            params["cue"] = cue
        response = await self.client.get(
            "/aliases",
            params=params,
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to get aliases: {response.text}")
        return response.json()

    async def merge_aliases(self, cues: List[str], to_cue: str) -> bool:
        """Merge aliases (async)."""
        response = await self.client.post(
            "/aliases/merge",
            json={"cues": cues, "to": to_cue},
            headers=self._headers()
        )
        return response.status_code == 200
    
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
