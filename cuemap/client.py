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
        query_text: Optional[str] = None,
        cues: Optional[List[str]] = None,
        projects: Optional[List[str]] = None,
        limit: int = 10,
        auto_reinforce: bool = False,
        min_intersection: Optional[int] = None,
        explain: bool = False,
        disable_pattern_completion: bool = False,
        disable_salience_bias: bool = False,
        disable_systems_consolidation: bool = False
    ) -> List[RecallResult]:
        """
        Recall memories by cues or natural language.
        
        Args:
            query_text: Natural language query to resolve via Lexicon
            cues: List of cues to search for
            projects: List of project IDs for cross-domain queries
            limit: Maximum results to return
            auto_reinforce: Automatically reinforce retrieved memories
            min_intersection: Minimum number of cues that must match
            explain: Include recall explanation in results
            
        Returns:
            List of recall results
            
        Example:
            >>> results = client.recall("payment failed", explain=True)
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
    
    # --- Lexicon Methods ---
    
    def lexicon_wire(self, token: str, canonical: str) -> Dict[str, Any]:
        """Manually wire a token to a canonical cue."""
        response = self.client.post(
            "/lexicon/wire",
            json={"token": token, "canonical": canonical},
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to wire lexicon: {response.text}")
        return response.json()

    def lexicon_inspect(self, cue: str) -> Dict[str, Any]:
        """Inspect a cue's relationships in the Lexicon."""
        response = self.client.get(
            f"/lexicon/inspect/{cue}",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to inspect lexicon: {response.text}")
        return response.json()

    def lexicon_graph(self) -> Dict[str, Any]:
        """Get the full Lexicon graph."""
        response = self.client.get(
            "/lexicon/graph",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to get lexicon graph: {response.text}")
        return response.json()

    def lexicon_synonyms(self, cue: str) -> Dict[str, Any]:
        """Get WordNet synonyms and graph suggestions for a cue."""
        response = self.client.get(
            f"/lexicon/synonyms/{cue}",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to get synonyms: {response.text}")
        return response.json()

    def lexicon_delete(self, memory_id: str) -> bool:
        """Delete a Lexicon entry."""
        response = self.client.delete(
            f"/lexicon/entry/{memory_id}",
            headers=self._headers()
        )
        return response.status_code == 200

    # --- Context & Backup Methods ---

    def context_expand(self, query: str, limit: int = 20, min_score: Optional[float] = None) -> Dict[str, Any]:
        """Expand a query using the cue co-occurrence graph."""
        payload = {"query": query, "limit": limit}
        if min_score is not None:
            payload["min_score"] = min_score
            
        response = self.client.post(
            "/context/expand",
            json=payload,
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to expand context: {response.text}")
        return response.json()

    def backup_upload(self, project_id: str) -> Dict[str, Any]:
        """Upload project snapshot to cloud backup."""
        response = self.client.post(
            "/backup/upload",
            json={"project_id": project_id},
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to upload backup: {response.text}")
        return response.json()

    def backup_download(self, project_id: str) -> Dict[str, Any]:
        """Download and load project snapshot from cloud backup."""
        response = self.client.post(
            "/backup/download",
            json={"project_id": project_id},
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to download backup: {response.text}")
        return response.json()

    def backup_list(self) -> Dict[str, Any]:
        """List available cloud backups."""
        response = self.client.get(
            "/backup/list",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to list backups: {response.text}")
        return response.json()
        
    def backup_delete(self, project_id: str) -> Dict[str, Any]:
        """Delete a cloud backup."""
        response = self.client.delete(
            f"/backup/{project_id}",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to delete backup: {response.text}")
        return response.json()

    # --- Ingestion Methods ---

    def ingest_url(self, url: str, depth: int = 0, same_domain_only: bool = True) -> Dict[str, Any]:
        """
        Ingest content from a URL with optional recursive crawling.
        
        Args:
            url: The URL to ingest
            depth: Crawl depth (0=single page, 1+=recursive crawling)
            same_domain_only: Only follow links within the same domain (default: True)
            
        Returns:
            Dict with status, chunks/pages_crawled, memory_ids, etc.
        """
        payload = {"url": url}
        if depth > 0:
            payload["depth"] = depth
            payload["same_domain_only"] = same_domain_only
            
        response = self.client.post(
            "/ingest/url",
            json=payload,
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to ingest URL: {response.text}")
        return response.json()

    def ingest_content(self, content: str, filename: str = "content.txt") -> Dict[str, Any]:
        """Ingest raw content."""
        response = self.client.post(
            "/ingest/content",
            json={"content": content, "filename": filename},
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to ingest content: {response.text}")
        return response.json()

    def ingest_file(self, file_path: str) -> Dict[str, Any]:
        """Ingest a file (PDF, DOCX, etc.) via upload."""
        import os
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            files = {"file": (filename, f)}
            response = self.client.post(
                "/ingest/file",
                files=files,
                headers=self._headers()
            )
        
        if response.status_code != 200:
            raise CueMapError(f"Failed to ingest file: {response.text}")
        return response.json()

    # --- Job Status ---

    def jobs_status(self) -> Dict[str, Any]:
        """Get background job status for the current project."""
        response = self.client.get(
            "/jobs/status",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to get job status: {response.text}")
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
        ...     results = await client.recall(cues=["work"])
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
        query_text: Optional[str] = None,
        cues: Optional[List[str]] = None,
        projects: Optional[List[str]] = None,
        limit: int = 10,
        auto_reinforce: bool = False,
        min_intersection: Optional[int] = None,
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
    
    async def lexicon_wire(self, token: str, canonical: str) -> Dict[str, Any]:
        """Manually wire a token to a canonical cue (async)."""
        response = await self.client.post(
            "/lexicon/wire",
            json={"token": token, "canonical": canonical},
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to wire lexicon: {response.text}")
        return response.json()

    async def lexicon_inspect(self, cue: str) -> Dict[str, Any]:
        """Inspect a cue's relationships in the Lexicon (async)."""
        response = await self.client.get(
            f"/lexicon/inspect/{cue}",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to inspect lexicon: {response.text}")
        return response.json()

    async def lexicon_graph(self) -> Dict[str, Any]:
        """Get the full Lexicon graph (async)."""
        response = await self.client.get(
            "/lexicon/graph",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to get lexicon graph: {response.text}")
        return response.json()

    async def lexicon_synonyms(self, cue: str) -> Dict[str, Any]:
        """Get WordNet synonyms and graph suggestions for a cue (async)."""
        response = await self.client.get(
            f"/lexicon/synonyms/{cue}",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to get synonyms: {response.text}")
        return response.json()

    async def lexicon_delete(self, memory_id: str) -> bool:
        """Delete a Lexicon entry (async)."""
        response = await self.client.delete(
            f"/lexicon/entry/{memory_id}",
            headers=self._headers()
        )
        return response.status_code == 200

    async def context_expand(self, query: str, limit: int = 20, min_score: Optional[float] = None) -> Dict[str, Any]:
        """Expand a query using the cue co-occurrence graph (async)."""
        payload = {"query": query, "limit": limit}
        if min_score is not None:
            payload["min_score"] = min_score
            
        response = await self.client.post(
            "/context/expand",
            json=payload,
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to expand context: {response.text}")
        return response.json()

    async def backup_upload(self, project_id: str) -> Dict[str, Any]:
        """Upload project snapshot to cloud backup (async)."""
        response = await self.client.post(
            "/backup/upload",
            json={"project_id": project_id},
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to upload backup: {response.text}")
        return response.json()

    async def backup_download(self, project_id: str) -> Dict[str, Any]:
        """Download and load project snapshot from cloud backup (async)."""
        response = await self.client.post(
            "/backup/download",
            json={"project_id": project_id},
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to download backup: {response.text}")
        return response.json()

    async def backup_list(self) -> Dict[str, Any]:
        """List available cloud backups (async)."""
        response = await self.client.get(
            "/backup/list",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to list backups: {response.text}")
        return response.json()
        
    async def backup_delete(self, project_id: str) -> Dict[str, Any]:
        """Delete a cloud backup (async)."""
        response = await self.client.delete(
            f"/backup/{project_id}",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to delete backup: {response.text}")
        return response.json()

    async def ingest_url(self, url: str, depth: int = 0, same_domain_only: bool = True) -> Dict[str, Any]:
        """
        Ingest content from a URL with optional recursive crawling (async).
        
        Args:
            url: The URL to ingest
            depth: Crawl depth (0=single page, 1+=recursive crawling)
            same_domain_only: Only follow links within the same domain (default: True)
            
        Returns:
            Dict with status, chunks/pages_crawled, memory_ids, etc.
        """
        payload = {"url": url}
        if depth > 0:
            payload["depth"] = depth
            payload["same_domain_only"] = same_domain_only
            
        response = await self.client.post(
            "/ingest/url",
            json=payload,
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to ingest URL: {response.text}")
        return response.json()

    async def ingest_content(self, content: str, filename: str = "content.txt") -> Dict[str, Any]:
        """Ingest raw content (async)."""
        response = await self.client.post(
            "/ingest/content",
            json={"content": content, "filename": filename},
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to ingest content: {response.text}")
        return response.json()

    async def ingest_file(self, file_path: str) -> Dict[str, Any]:
        """Ingest a file (PDF, DOCX, etc.) via upload (async)."""
        import os
        filename = os.path.basename(file_path)
        # Note: httpx.AsyncClient file upload usage
        with open(file_path, "rb") as f:
            # We must read content into memory for async upload if we don't use a stream wrapper,
            # but standard open() file object might work with recent httpx.
            # Safest for small files is reading bytes.
            file_content = f.read()
            
        files = {"file": (filename, file_content)}
        response = await self.client.post(
            "/ingest/file",
            files=files,
            headers=self._headers()
        )
        
        if response.status_code != 200:
            raise CueMapError(f"Failed to ingest file: {response.text}")
        return response.json()

    async def jobs_status(self) -> Dict[str, Any]:
        """Get background job status for the current project (async)."""
        response = await self.client.get(
            "/jobs/status",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to get job status: {response.text}")
        return response.json()

    async def close(self):
        """Close the client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
