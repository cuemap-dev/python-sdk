"""Pure CueMap client - no magic, just speed."""

import httpx
from typing import List, Optional, Dict, Any

from .models import Memory, RecallResult
from .exceptions import CueMapError, ConnectionError, AuthenticationError


def _clean_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset values while preserving explicit false/zero values."""
    return {key: value for key, value in payload.items() if value is not None}


class CueMap:
    """
    Pure CueMap client.
    
    The engine performs deterministic cue extraction and can use its bundled
    local MiniLM encoder for semantic retrieval when configured.
    
    Example:
        >>> client = CueMap()
        >>> client.add("Important note", cues=["work", "urgent"])
        >>> results = client.recall(cues=["work"])
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
        cues: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        disable_temporal_chunking: bool = False,
        source_key: Optional[str] = None,
        event_time: Optional[float] = None,
        embedding: Optional[List[float]] = None,
        async_ingest: bool = False,
        minimal_response: bool = False,
        trace_timing: bool = False,
    ) -> Any:
        """
        Add a memory.
        
        Args:
            content: Memory content
            cues: Optional list of cues (tags) for retrieval
            metadata: Optional metadata
            event_time: Original event timestamp as Unix seconds. Defaults to ingestion time.
            
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
            json=_clean_payload({
                "content": content,
                "cues": cues or [],
                "metadata": metadata,
                "disable_temporal_chunking": disable_temporal_chunking,
                "source_key": source_key,
                "event_time": event_time,
                "embedding": embedding,
                "async_ingest": async_ingest,
                "minimal_response": minimal_response,
                "trace_timing": trace_timing,
            }),
            headers=self._headers()
        )
        
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code != 200:
            raise CueMapError(f"Failed to add memory: {response.status_code}")
        
        return response.json()["id"]

    def add_batch(
        self,
        memories: List[Dict[str, Any]],
        minimal_response: bool = False,
        trace_timing: bool = False,
    ) -> Dict[str, Any]:
        """Add multiple memories in one request."""
        response = self.client.post(
            "/memories/batch",
            json={
                "memories": memories,
                "minimal_response": minimal_response,
                "trace_timing": trace_timing,
            },
            headers=self._headers()
        )

        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code != 200:
            raise CueMapError(f"Failed to add memories: {response.text}")

        return response.json()

    def classify_intent(
        self,
        text: str,
        target: str = "query",
    ) -> Dict[str, Any]:
        """Classify query or memory intent with the engine's local model."""
        response = self.client.post(
            "/intent/classify",
            json={"text": text, "target": target},
            headers=self._headers(),
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to classify intent: {response.text}")
        return response.json()
    
    def recall(
        self,
        query_text: Optional[str] = None,
        cues: Optional[List[str]] = None,
        projects: Optional[List[str]] = None,
        query_time: Optional[str] = None,
        limit: int = 10,
        depth: int = 1,
        auto_reinforce: bool = False,
        min_intersection: Optional[int] = None,
        explain: bool = False,
        disable_salience_bias: bool = False,
        disable_alias_expansion: bool = True,
        trace_timing: bool = False,
        expansion_depth: int = 1,
        parent_fusion: str = "off",
        parent_fusion_limit: int = 80,
        parent_fusion_min_chunks: int = 2,
        ordered_reconstruction: str = "off",
        ordered_reconstruction_limit: int = 80,
        ordered_session_scan_limit: int = 4096,
        ordered_max_sessions: int = 3,
        evidence_coverage: str = "off",
        evidence_coverage_limit: int = 100,
        evidence_coverage_session_scan_limit: int = 4096,
        evidence_coverage_max_sessions: int = 3,
        disable_cuebridge_artifacts: bool = False,
        cuebridge_gap_limit: int = 6,
        disable_pattern_completion: Optional[bool] = None,
        disable_systems_consolidation: Optional[bool] = None,
        semantic_mode: str = "hybrid",
        query_embedding: Optional[List[float]] = None,
    ) -> List[RecallResult]:
        """
        Recall memories by cues or natural language.
        
        Args:
            query_text: Natural language query to resolve via Lexicon
            cues: List of cues to search for
            projects: List of project IDs for cross-domain queries
            limit: Maximum results to return
            depth: Number of multi-hop recall expansion hops
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
            "depth": depth,
            "auto_reinforce": auto_reinforce,
            "explain": explain,
            "disable_salience_bias": disable_salience_bias,
            "disable_alias_expansion": disable_alias_expansion,
            "trace_timing": trace_timing,
            "expansion_depth": expansion_depth,
            "parent_fusion": parent_fusion,
            "parent_fusion_limit": parent_fusion_limit,
            "parent_fusion_min_chunks": parent_fusion_min_chunks,
            "ordered_reconstruction": ordered_reconstruction,
            "ordered_reconstruction_limit": ordered_reconstruction_limit,
            "ordered_session_scan_limit": ordered_session_scan_limit,
            "ordered_max_sessions": ordered_max_sessions,
            "evidence_coverage": evidence_coverage,
            "evidence_coverage_limit": evidence_coverage_limit,
            "evidence_coverage_session_scan_limit": evidence_coverage_session_scan_limit,
            "evidence_coverage_max_sessions": evidence_coverage_max_sessions,
            "disable_cuebridge_artifacts": disable_cuebridge_artifacts,
            "cuebridge_gap_limit": cuebridge_gap_limit,
            "semantic_mode": semantic_mode,
            "query_embedding": query_embedding,
        }
        if cues:
            payload["cues"] = cues
        if query_text:
            payload["query_text"] = query_text
        if query_time:
            payload["query_time"] = query_time
        if min_intersection is not None:
            payload["min_intersection"] = min_intersection
        if projects:
            payload["projects"] = projects
        response = self.client.post(
            "/recall",
            json=_clean_payload(payload),
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
        auto_reinforce: bool = True,
        min_intersection: Optional[int] = None,
        disable_salience_bias: bool = False,
        disable_alias_expansion: bool = True,
        expansion_depth: int = 1,
        disable_pattern_completion: Optional[bool] = None,
        disable_systems_consolidation: Optional[bool] = None,
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
            json=_clean_payload({
                "query_text": query,
                "token_budget": token_budget,
                "limit": limit,
                "projects": projects,
                "auto_reinforce": auto_reinforce,
                "min_intersection": min_intersection,
                "disable_salience_bias": disable_salience_bias,
                "disable_alias_expansion": disable_alias_expansion,
                "expansion_depth": expansion_depth,
            }),
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

    def create_project(self, project_id: str) -> Dict[str, Any]:
        """Create a project."""
        response = self.client.post(
            "/projects",
            json={"project_id": project_id},
            headers=self._headers()
        )
        if response.status_code not in (200, 201):
            raise CueMapError(f"Failed to create project: {response.text}")
        return response.json()

    def delete_project(self, project_id: str) -> bool:
        """Delete a project (multi-tenant only)."""
        response = self.client.delete(
            f"/projects/{project_id}",
            headers=self._headers()
        )
        return response.status_code == 200

    def project_artifacts(self, project_id: str) -> Dict[str, Any]:
        """Get CueBridge artifact summary for a project."""
        response = self.client.get(
            f"/projects/{project_id}/artifacts",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to get project artifacts: {response.text}")
        return response.json()

    def reload_project_artifacts(self, project_id: str) -> Dict[str, Any]:
        """Reload CueBridge artifacts for a project."""
        response = self.client.post(
            f"/projects/{project_id}/artifacts",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to reload project artifacts: {response.text}")
        return response.json()

    def export_project(
        self,
        project_id: str,
        cursor: Optional[int] = None,
        limit: int = 1000,
        include_content: bool = True,
        include_cues: bool = True,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """Export project memories with cursor pagination."""
        response = self.client.get(
            f"/projects/{project_id}/export",
            params=_clean_payload({
                "cursor": cursor,
                "limit": limit,
                "include_content": include_content,
                "include_cues": include_cues,
                "include_metadata": include_metadata,
            }),
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to export project: {response.text}")
        return response.json()

    def set_project_watch_dir(
        self,
        project_id: str,
        watch_dir: str,
        ignored_patterns: Optional[List[str]] = None,
        ignored_extensions: Optional[List[str]] = None,
        included_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Set the self-learning agent watch directory for a project."""
        response = self.client.post(
            f"/projects/{project_id}/watch-dir",
            json=_clean_payload({
                "watch_dir": watch_dir,
                "included_paths": included_paths,
                "ignored_patterns": ignored_patterns,
                "ignored_extensions": ignored_extensions,
            }),
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to set project watch directory: {response.text}")
        return response.json()

    def get_project_watch_dir(self, project_id: str) -> Dict[str, Any]:
        """Read a project's persisted repository ingestion scope."""
        response = self.client.get(
            f"/projects/{project_id}/watch-dir",
            headers=self._headers(),
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to get project watch directory: {response.text}")
        return response.json()

    def preview_directory(
        self,
        watch_dir: str,
        included_paths: Optional[List[str]] = None,
        ignored_patterns: Optional[List[str]] = None,
        ignored_extensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Preview supported repository files without ingesting content."""
        response = self.client.post(
            "/ingest/directory/preview",
            json=_clean_payload({
                "watch_dir": watch_dir,
                "included_paths": included_paths,
                "ignored_patterns": ignored_patterns,
                "ignored_extensions": ignored_extensions,
            }),
            headers=self._headers(),
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to preview directory: {response.text}")
        return response.json()

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

    def lexicon_delete(self, memory_id: str) -> bool:
        """Delete a Lexicon entry."""
        response = self.client.delete(
            f"/lexicon/entry/{memory_id}",
            headers=self._headers()
        )
        return response.status_code == 200

    # --- Backup Methods ---

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

    def ingest_content(
        self,
        content: str,
        filename: str = "content.txt",
        source_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        structural_cues: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        segmenter: str = "sentence_window",
        segment_window_size: Optional[int] = None,
        segment_overlap: Optional[int] = None,
        segment_min_chunk_chars: Optional[int] = None,
        segment_max_chunk_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Ingest raw content."""
        response = self.client.post(
            "/ingest/content",
            json=_clean_payload({
                "content": content,
                "filename": filename,
                "source_key": source_key,
                "metadata": metadata,
                "structural_cues": structural_cues,
                "embeddings": embeddings,
                "segmenter": segmenter,
                "segment_window_size": segment_window_size,
                "segment_overlap": segment_overlap,
                "segment_min_chunk_chars": segment_min_chunk_chars,
                "segment_max_chunk_chars": segment_max_chunk_chars,
            }),
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to ingest content: {response.text}")
        return response.json()

    def recall_web(
        self,
        query: str,
        url: Optional[str] = None,
        persist: bool = False,
    ) -> Dict[str, Any]:
        """Recall directly from a URL or web search result set."""
        response = self.client.post(
            "/recall/web",
            json=_clean_payload({"query": query, "url": url, "persist": persist}),
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to recall web context: {response.text}")
        return response.json()

    def debug_analyze_text(
        self,
        text: str,
        query_time: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        existing_cues: Optional[List[str]] = None,
        available_cues: Optional[List[str]] = None,
        filename: Optional[str] = None,
        segmenter: str = "sentence_window",
        segment_window_size: Optional[int] = None,
        segment_overlap: Optional[int] = None,
        segment_min_chunk_chars: Optional[int] = None,
        segment_max_chunk_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Analyze v0.7 cue extraction, query intent, and chunking for text."""
        response = self.client.post(
            "/debug/analyze-text",
            json=_clean_payload({
                "text": text,
                "query_time": query_time,
                "metadata": metadata,
                "existing_cues": existing_cues,
                "available_cues": available_cues,
                "filename": filename,
                "segmenter": segmenter,
                "segment_window_size": segment_window_size,
                "segment_overlap": segment_overlap,
                "segment_min_chunk_chars": segment_min_chunk_chars,
                "segment_max_chunk_chars": segment_max_chunk_chars,
            }),
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to analyze text: {response.text}")
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
        cues: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        disable_temporal_chunking: bool = False,
        source_key: Optional[str] = None,
        event_time: Optional[float] = None,
        embedding: Optional[List[float]] = None,
        async_ingest: bool = False,
        minimal_response: bool = False,
        trace_timing: bool = False,
    ) -> Any:
        """Add a memory (async)."""
        response = await self.client.post(
            "/memories",
            json=_clean_payload({
                "content": content,
                "cues": cues or [],
                "metadata": metadata,
                "disable_temporal_chunking": disable_temporal_chunking,
                "source_key": source_key,
                "event_time": event_time,
                "embedding": embedding,
                "async_ingest": async_ingest,
                "minimal_response": minimal_response,
                "trace_timing": trace_timing,
            }),
            headers=self._headers()
        )
        
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code != 200:
            raise CueMapError(f"Failed to add memory: {response.status_code}")
        
        return response.json()["id"]

    async def add_batch(
        self,
        memories: List[Dict[str, Any]],
        minimal_response: bool = False,
        trace_timing: bool = False,
    ) -> Dict[str, Any]:
        """Add multiple memories in one request (async)."""
        response = await self.client.post(
            "/memories/batch",
            json={
                "memories": memories,
                "minimal_response": minimal_response,
                "trace_timing": trace_timing,
            },
            headers=self._headers()
        )

        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code != 200:
            raise CueMapError(f"Failed to add memories: {response.text}")

        return response.json()

    async def classify_intent(
        self,
        text: str,
        target: str = "query",
    ) -> Dict[str, Any]:
        """Classify query or memory intent with the engine's local model (async)."""
        response = await self.client.post(
            "/intent/classify",
            json={"text": text, "target": target},
            headers=self._headers(),
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to classify intent: {response.text}")
        return response.json()
    
    async def recall(
        self,
        query_text: Optional[str] = None,
        cues: Optional[List[str]] = None,
        projects: Optional[List[str]] = None,
        query_time: Optional[str] = None,
        limit: int = 10,
        depth: int = 1,
        auto_reinforce: bool = False,
        min_intersection: Optional[int] = None,
        explain: bool = False,
        disable_salience_bias: bool = False,
        disable_alias_expansion: bool = True,
        trace_timing: bool = False,
        expansion_depth: int = 1,
        parent_fusion: str = "off",
        parent_fusion_limit: int = 80,
        parent_fusion_min_chunks: int = 2,
        ordered_reconstruction: str = "off",
        ordered_reconstruction_limit: int = 80,
        ordered_session_scan_limit: int = 4096,
        ordered_max_sessions: int = 3,
        evidence_coverage: str = "off",
        evidence_coverage_limit: int = 100,
        evidence_coverage_session_scan_limit: int = 4096,
        evidence_coverage_max_sessions: int = 3,
        disable_cuebridge_artifacts: bool = False,
        cuebridge_gap_limit: int = 6,
        disable_pattern_completion: Optional[bool] = None,
        disable_systems_consolidation: Optional[bool] = None,
        semantic_mode: str = "hybrid",
        query_embedding: Optional[List[float]] = None,
    ) -> List[RecallResult]:
        """Recall memories (async)."""
        payload = {
            "limit": limit,
            "depth": depth,
            "auto_reinforce": auto_reinforce,
            "explain": explain,
            "disable_salience_bias": disable_salience_bias,
            "disable_alias_expansion": disable_alias_expansion,
            "trace_timing": trace_timing,
            "expansion_depth": expansion_depth,
            "parent_fusion": parent_fusion,
            "parent_fusion_limit": parent_fusion_limit,
            "parent_fusion_min_chunks": parent_fusion_min_chunks,
            "ordered_reconstruction": ordered_reconstruction,
            "ordered_reconstruction_limit": ordered_reconstruction_limit,
            "ordered_session_scan_limit": ordered_session_scan_limit,
            "ordered_max_sessions": ordered_max_sessions,
            "evidence_coverage": evidence_coverage,
            "evidence_coverage_limit": evidence_coverage_limit,
            "evidence_coverage_session_scan_limit": evidence_coverage_session_scan_limit,
            "evidence_coverage_max_sessions": evidence_coverage_max_sessions,
            "disable_cuebridge_artifacts": disable_cuebridge_artifacts,
            "cuebridge_gap_limit": cuebridge_gap_limit,
            "semantic_mode": semantic_mode,
            "query_embedding": query_embedding,
        }
        if cues:
            payload["cues"] = cues
        if query_text:
            payload["query_text"] = query_text
        if query_time:
            payload["query_time"] = query_time
        if min_intersection is not None:
            payload["min_intersection"] = min_intersection
        if projects:
            payload["projects"] = projects
        response = await self.client.post(
            "/recall",
            json=_clean_payload(payload),
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
        auto_reinforce: bool = True,
        min_intersection: Optional[int] = None,
        disable_salience_bias: bool = False,
        disable_alias_expansion: bool = True,
        expansion_depth: int = 1,
        disable_pattern_completion: Optional[bool] = None,
        disable_systems_consolidation: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Recall grounded context (async)."""
        response = await self.client.post(
            "/recall/grounded",
            json=_clean_payload({
                "query_text": query,
                "token_budget": token_budget,
                "limit": limit,
                "projects": projects,
                "auto_reinforce": auto_reinforce,
                "min_intersection": min_intersection,
                "disable_salience_bias": disable_salience_bias,
                "disable_alias_expansion": disable_alias_expansion,
                "expansion_depth": expansion_depth,
            }),
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

    async def create_project(self, project_id: str) -> Dict[str, Any]:
        """Create a project (async)."""
        response = await self.client.post(
            "/projects",
            json={"project_id": project_id},
            headers=self._headers()
        )
        if response.status_code not in (200, 201):
            raise CueMapError(f"Failed to create project: {response.text}")
        return response.json()

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project (async, multi-tenant only)."""
        response = await self.client.delete(
            f"/projects/{project_id}",
            headers=self._headers()
        )
        return response.status_code == 200

    async def project_artifacts(self, project_id: str) -> Dict[str, Any]:
        """Get CueBridge artifact summary for a project (async)."""
        response = await self.client.get(
            f"/projects/{project_id}/artifacts",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to get project artifacts: {response.text}")
        return response.json()

    async def reload_project_artifacts(self, project_id: str) -> Dict[str, Any]:
        """Reload CueBridge artifacts for a project (async)."""
        response = await self.client.post(
            f"/projects/{project_id}/artifacts",
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to reload project artifacts: {response.text}")
        return response.json()

    async def export_project(
        self,
        project_id: str,
        cursor: Optional[int] = None,
        limit: int = 1000,
        include_content: bool = True,
        include_cues: bool = True,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """Export project memories with cursor pagination (async)."""
        response = await self.client.get(
            f"/projects/{project_id}/export",
            params=_clean_payload({
                "cursor": cursor,
                "limit": limit,
                "include_content": include_content,
                "include_cues": include_cues,
                "include_metadata": include_metadata,
            }),
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to export project: {response.text}")
        return response.json()

    async def set_project_watch_dir(
        self,
        project_id: str,
        watch_dir: str,
        ignored_patterns: Optional[List[str]] = None,
        ignored_extensions: Optional[List[str]] = None,
        included_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Set the self-learning agent watch directory for a project (async)."""
        response = await self.client.post(
            f"/projects/{project_id}/watch-dir",
            json=_clean_payload({
                "watch_dir": watch_dir,
                "included_paths": included_paths,
                "ignored_patterns": ignored_patterns,
                "ignored_extensions": ignored_extensions,
            }),
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to set project watch directory: {response.text}")
        return response.json()

    async def get_project_watch_dir(self, project_id: str) -> Dict[str, Any]:
        """Read a project's persisted repository ingestion scope (async)."""
        response = await self.client.get(
            f"/projects/{project_id}/watch-dir",
            headers=self._headers(),
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to get project watch directory: {response.text}")
        return response.json()

    async def preview_directory(
        self,
        watch_dir: str,
        included_paths: Optional[List[str]] = None,
        ignored_patterns: Optional[List[str]] = None,
        ignored_extensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Preview supported repository files without ingesting content (async)."""
        response = await self.client.post(
            "/ingest/directory/preview",
            json=_clean_payload({
                "watch_dir": watch_dir,
                "included_paths": included_paths,
                "ignored_patterns": ignored_patterns,
                "ignored_extensions": ignored_extensions,
            }),
            headers=self._headers(),
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to preview directory: {response.text}")
        return response.json()

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

    async def lexicon_delete(self, memory_id: str) -> bool:
        """Delete a Lexicon entry (async)."""
        response = await self.client.delete(
            f"/lexicon/entry/{memory_id}",
            headers=self._headers()
        )
        return response.status_code == 200

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

    async def ingest_content(
        self,
        content: str,
        filename: str = "content.txt",
        source_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        structural_cues: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        segmenter: str = "sentence_window",
        segment_window_size: Optional[int] = None,
        segment_overlap: Optional[int] = None,
        segment_min_chunk_chars: Optional[int] = None,
        segment_max_chunk_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Ingest raw content (async)."""
        response = await self.client.post(
            "/ingest/content",
            json=_clean_payload({
                "content": content,
                "filename": filename,
                "source_key": source_key,
                "metadata": metadata,
                "structural_cues": structural_cues,
                "embeddings": embeddings,
                "segmenter": segmenter,
                "segment_window_size": segment_window_size,
                "segment_overlap": segment_overlap,
                "segment_min_chunk_chars": segment_min_chunk_chars,
                "segment_max_chunk_chars": segment_max_chunk_chars,
            }),
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to ingest content: {response.text}")
        return response.json()

    async def recall_web(
        self,
        query: str,
        url: Optional[str] = None,
        persist: bool = False,
    ) -> Dict[str, Any]:
        """Recall directly from a URL or web search result set (async)."""
        response = await self.client.post(
            "/recall/web",
            json=_clean_payload({"query": query, "url": url, "persist": persist}),
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to recall web context: {response.text}")
        return response.json()

    async def debug_analyze_text(
        self,
        text: str,
        query_time: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        existing_cues: Optional[List[str]] = None,
        available_cues: Optional[List[str]] = None,
        filename: Optional[str] = None,
        segmenter: str = "sentence_window",
        segment_window_size: Optional[int] = None,
        segment_overlap: Optional[int] = None,
        segment_min_chunk_chars: Optional[int] = None,
        segment_max_chunk_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Analyze v0.7 cue extraction, query intent, and chunking for text (async)."""
        response = await self.client.post(
            "/debug/analyze-text",
            json=_clean_payload({
                "text": text,
                "query_time": query_time,
                "metadata": metadata,
                "existing_cues": existing_cues,
                "available_cues": available_cues,
                "filename": filename,
                "segmenter": segmenter,
                "segment_window_size": segment_window_size,
                "segment_overlap": segment_overlap,
                "segment_min_chunk_chars": segment_min_chunk_chars,
                "segment_max_chunk_chars": segment_max_chunk_chars,
            }),
            headers=self._headers()
        )
        if response.status_code != 200:
            raise CueMapError(f"Failed to analyze text: {response.text}")
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
