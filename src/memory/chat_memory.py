"""Chat memory helpers for short- and long-term recall."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

from data.db import Database

try:
    from memory.vector_store import VectorMemory  # type: ignore
except Exception:  # pragma: no cover
    VectorMemory = None  # type: ignore


class ChatMemory:
    """Stores chat history locally and optionally in vector memory."""

    def __init__(
        self,
        db: Optional[Database] = None,
        vector_memory: Optional["VectorMemory"] = None,
    ):
        self.db = db or Database()
        self.vector_memory = vector_memory
        self.logger = logging.getLogger("futureoracle.chat_memory")

    def store_message(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        tickers: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            self.db.save_chat_message(
                session_id=session_id,
                role=role,
                content=content,
                intent=intent,
                tickers=tickers or [],
                metadata=metadata or {},
            )
        except Exception as exc:
            self.logger.debug(f"Chat memory store skipped: {exc}")

    def store_summary(self, summary_text: str, metadata: Dict[str, Any]) -> None:
        if not summary_text:
            return
        if self.vector_memory is None:
            return
        try:
            tickers = metadata.get("tickers") or ["CHAT"]
            ticker = metadata.get("ticker") or tickers[0]
            self.vector_memory.store_analysis(
                ticker=ticker,
                analysis_text=summary_text,
                metadata=metadata,
            )
        except Exception as exc:
            self.logger.debug(f"Vector memory store skipped: {exc}")

    def retrieve_similar(self, query_text: str, top_k: int = 5, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.vector_memory is not None:
            try:
                return self.vector_memory.retrieve_similar_analyses(
                    query_text=query_text,
                    top_k=top_k,
                    ticker=ticker,
                )
            except Exception as exc:
                self.logger.debug(f"Vector memory query skipped: {exc}")

        try:
            return self.db.search_chat_messages(query_text, limit=top_k)
        except Exception:
            return []
