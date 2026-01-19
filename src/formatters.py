"""Chat response formatting utilities."""

from __future__ import annotations

from typing import Iterable, List, Optional


def _ensure_bullets(items: Optional[Iterable[str]], fallback: str) -> List[str]:
    if not items:
        return [fallback]
    cleaned = [item.strip() for item in items if item and item.strip()]
    return cleaned if cleaned else [fallback]


def format_chat_response(
    tldr: str,
    why: Optional[Iterable[str]] = None,
    assumptions: Optional[Iterable[str]] = None,
    confidence: Optional[str] = None,
    next_steps: Optional[str] = None,
    evidence: Optional[Iterable[str]] = None,
    glossary: Optional[Iterable[str]] = None,
    disclaimers: Optional[Iterable[str]] = None,
) -> str:
    """Format a chat response with the required explainability blocks."""
    confidence_text = confidence or "Medium"
    why_items = _ensure_bullets(why, "This focuses on the highest-signal items available.")
    assumption_items = _ensure_bullets(assumptions, "Based on public data and recent headlines.")

    parts: List[str] = []
    parts.append(f"TL;DR: {tldr}")
    parts.append("Why it matters:")
    parts.extend([f"- {item}" for item in why_items])
    parts.append("Assumptions:")
    parts.extend([f"- {item}" for item in assumption_items])
    parts.append(f"Confidence: {confidence_text}")

    if evidence:
        parts.append("Evidence:")
        parts.extend([f"- {item}" for item in _ensure_bullets(evidence, "No source links available.")])

    if glossary:
        parts.append("Glossary:")
        parts.extend([f"- {item}" for item in _ensure_bullets(glossary, "No glossary terms added.")])

    if next_steps:
        parts.append(f"Next: {next_steps}")

    if disclaimers:
        for disclaimer in _ensure_bullets(disclaimers, ""):
            if disclaimer:
                parts.append(f"_{disclaimer}_")

    return "\n".join(parts)
