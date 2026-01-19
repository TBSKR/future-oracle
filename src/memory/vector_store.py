"""
Vector memory store backed by Pinecone.

Stores analyses as embeddings for long-term retrieval.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    from pinecone import Pinecone  # type: ignore
except Exception:  # pragma: no cover
    Pinecone = None  # type: ignore


class VectorMemory:
    """
    Vector memory using Pinecone and OpenAI embeddings.

    Required env vars:
    - PINECONE_API_KEY
    - PINECONE_INDEX_NAME
    - OPENAI_API_KEY
    """

    def __init__(
        self,
        index_name: Optional[str] = None,
        namespace: str = "analyses",
        dimension: int = 1536,
        metric: str = "cosine",
        embedding_model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        self.logger = logging.getLogger("futureoracle.vector_memory")

        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.index_name = index_name or os.getenv("PINECONE_INDEX_NAME")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("PINECONE_API_KEY not set")
        if not self.index_name:
            raise ValueError("PINECONE_INDEX_NAME not set")
        if OpenAI is None:
            raise ImportError("openai package not installed")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set")
        if Pinecone is None:
            raise ImportError("pinecone-client not installed")

        self.embedding_model = embedding_model
        self.namespace = namespace
        self.dimension = dimension
        self.metric = metric

        self.openai_client = OpenAI(api_key=self.openai_api_key)
        self.index = self._init_pinecone_index()

    def store_analysis(self, ticker: str, analysis_text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store a completed analysis in Pinecone.

        Args:
            ticker: Stock ticker or tag for the analysis
            analysis_text: Full analysis text to embed
            metadata: Additional metadata to store alongside the vector

        Returns:
            Vector ID used for the upsert.
        """
        cleaned_metadata = self._sanitize_metadata(metadata or {})
        cleaned_metadata.setdefault("ticker", ticker)
        cleaned_metadata.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

        analysis_text = (analysis_text or "").strip()
        cleaned_metadata["analysis_text"] = self._truncate_text(analysis_text, 2000)
        cleaned_metadata.setdefault(
            "summary",
            self._truncate_text(
                cleaned_metadata.get("key_insight") or analysis_text,
                280,
            ),
        )

        vector_id = cleaned_metadata.get("id") or self._build_vector_id(ticker, analysis_text)
        embedding = self._embed_text(analysis_text)

        self.index.upsert(
            vectors=[(vector_id, embedding, cleaned_metadata)],
            namespace=self.namespace,
        )

        return vector_id

    def retrieve_similar_analyses(
        self,
        query_text: str,
        top_k: int = 5,
        ticker: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar analyses using vector similarity.

        Args:
            query_text: Text to search against stored analyses
            top_k: Number of results to return
            ticker: Optional ticker filter

        Returns:
            List of matches with id, score, and metadata.
        """
        embedding = self._embed_text(query_text)
        metadata_filter = {"ticker": {"$eq": ticker}} if ticker else None

        query_kwargs = {
            "vector": embedding,
            "top_k": top_k,
            "include_metadata": True,
            "namespace": self.namespace,
        }
        if metadata_filter:
            query_kwargs["filter"] = metadata_filter

        result = self.index.query(**query_kwargs)

        matches = result.get("matches", []) if isinstance(result, dict) else result.matches
        return [self._normalize_match(match) for match in matches]

    def _init_pinecone_index(self):
        """Initialize Pinecone index using v3 client syntax."""
        pc = Pinecone(api_key=self.api_key)
        return pc.Index(self.index_name)

    def _embed_text(self, text: str) -> List[float]:
        if not text:
            text = " "
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return response.data[0].embedding

    def _build_vector_id(self, ticker: str, analysis_text: str) -> str:
        payload = f"{ticker}|{analysis_text}".encode("utf-8", errors="ignore")
        return hashlib.sha256(payload).hexdigest()[:32]

    def _normalize_match(self, match: Any) -> Dict[str, Any]:
        if isinstance(match, dict):
            return {
                "id": match.get("id"),
                "score": match.get("score"),
                "metadata": match.get("metadata", {}) or {},
            }

        return {
            "id": getattr(match, "id", None),
            "score": getattr(match, "score", None),
            "metadata": getattr(match, "metadata", {}) or {},
        }

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        def _clean(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, dict):
                return {str(k): _clean(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [_clean(v) for v in value]
            return value

        return {str(key): _clean(value) for key, value in metadata.items()}

    def _truncate_text(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 3].rstrip() + "..."
