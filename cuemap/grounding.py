from typing import List, Optional, Dict, Any
from .client import CueMap, AsyncCueMap

class CueMapGroundingRetriever:
    """
    Tiny library for Relevance Compression & Grounding.
    
    Acts as a middleware for LLM pipelines (LangChain/LlamaIndex style).
    """

    def __init__(self, client: Optional[CueMap] = None, **kwargs):
        """
        Initialize the retriever.
        
        Args:
            client: Existing CueMap client instance
            **kwargs: Arguments to create a new CueMap client if none provided
        """
        self.client = client or CueMap(**kwargs)

    def retrieve_grounded(
        self,
        query_text: str,
        token_budget: int = 500,
        limit: int = 10,
        projects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        The main entry point for grounded context.
        
        Returns:
            - verified_context_block (string): Formatted for prompts
            - grounding_proof (JSON/Dict): For audit trails
            - selected_memories (list): Raw memory objects
        """
        raw_response = self.client.recall_grounded(
            query=query_text,
            token_budget=token_budget,
            limit=limit,
            projects=projects
        )

        return {
            "verified_context_block": raw_response["verified_context"],
            "grounding_proof": raw_response["proof"],
            "selected_memories": raw_response["proof"].get("selected", [])
        }


class AsyncCueMapGroundingRetriever:
    """Async version of the Grounding Retriever."""

    def __init__(self, client: Optional[AsyncCueMap] = None, **kwargs):
        self.client = client or AsyncCueMap(**kwargs)

    async def retrieve_grounded(
        self,
        query_text: str,
        token_budget: int = 500,
        limit: int = 10,
        projects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        raw_response = await self.client.recall_grounded(
            query=query_text,
            token_budget=token_budget,
            limit=limit,
            projects=projects
        )

        return {
            "verified_context_block": raw_response["verified_context"],
            "grounding_proof": raw_response["proof"],
            "selected_memories": raw_response["proof"].get("selected", [])
        }
