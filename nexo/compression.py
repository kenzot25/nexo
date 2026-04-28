"""Context compression for multi-turn conversations.

Implements token budget management by summarizing older turns
while preserving important slot values and recent context.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Turn:
    """A single conversation turn."""
    turn_id: int
    user_input: str
    ai_response: str
    matched_nodes: list[str] | None = None
    collected_slots: dict[str, Any] | None = None


def compress_conversation(
    turns: list[Turn],
    token_budget: int = 2000,
    required_fields: list[str] | None = None,
    keep_recent_turns: int = 5,
) -> str:
    """Compress conversation history to fit within token budget.

    Strategy:
    1. Keep the last N turns intact (default 5)
    2. Summarize older turns, preserving required fields (slots, goals)
    3. Maintain conversation flow and key information

    Args:
        turns: List of conversation turns
        token_budget: Maximum tokens allowed (approx 4 chars per token)
        required_fields: Field names to preserve in summary (e.g., ["collected_slots", "current_goal"])
        keep_recent_turns: Number of recent turns to keep verbatim

    Returns:
        Compressed conversation text
    """
    required_fields = required_fields or ["collected_slots", "current_goal"]

    if not turns:
        return ""

    # Calculate character budget (rough estimate: 1 token ≈ 4 chars)
    char_budget = token_budget * 4

    # Split turns into old and recent
    old_turns = turns[:-keep_recent_turns] if len(turns) > keep_recent_turns else []
    recent_turns = turns[-keep_recent_turns:]

    # Build compressed output
    parts = []

    # Add summary of old turns if any
    if old_turns:
        summary = _summarize_old_turns(old_turns, required_fields)
        parts.append(f"[Conversation Summary - {len(old_turns)} turns]\n{summary}\n")

    # Add recent turns verbatim
    for turn in recent_turns:
        parts.append(_turn_to_text(turn))

    result = "\n".join(parts)

    # Truncate if still over budget
    if len(result) > char_budget:
        result = result[:char_budget] + "\n... (truncated to token budget)"

    return result


def _summarize_old_turns(
    turns: list[Turn],
    required_fields: list[str],
) -> str:
    """Summarize old turns while preserving required fields.

    Args:
        turns: Old turns to summarize
        required_fields: Fields to extract and preserve

    Returns:
        Summary text
    """
    # Collect all slots and key info
    all_slots: dict[str, Any] = {}
    mentioned_nodes: set[str] = set()
    turn_count = len(turns)

    for turn in turns:
        if turn.collected_slots:
            all_slots.update(turn.collected_slots)
        if turn.matched_nodes:
            mentioned_nodes.update(turn.matched_nodes)

    # Build summary
    summary_parts = [
        f"Previous conversation: {turn_count} turns",
    ]

    if all_slots:
        slots_text = ", ".join(f"{k}={v}" for k, v in all_slots.items())
        summary_parts.append(f"Collected information: {slots_text}")

    if mentioned_nodes:
        summary_parts.append(f"Topics discussed: {', '.join(sorted(mentioned_nodes))}")

    return "\n".join(summary_parts)


def _turn_to_text(turn: Turn) -> str:
    """Convert a single turn to text format."""
    lines = [
        f"[Turn {turn.turn_id}]",
        f"User: {turn.user_input}",
        f"AI: {turn.ai_response}",
    ]

    if turn.matched_nodes:
        lines.append(f"Matched: {', '.join(turn.matched_nodes)}")

    if turn.collected_slots:
        slots = ", ".join(f"{k}={v}" for k, v in turn.collected_slots.items())
        lines.append(f"Slots: {slots}")

    return "\n".join(lines)


def should_compress(
    turns: list[Turn],
    token_budget: int = 2000,
    threshold: float = 0.8,
) -> bool:
    """Check if compression should be triggered.

    Triggers compression when current usage exceeds threshold * budget.

    Args:
        turns: Current conversation turns
        token_budget: Maximum tokens allowed
        threshold: Trigger compression at this fraction of budget (default 80%)

    Returns:
        True if compression is needed
    """
    current_text = "\n".join(_turn_to_text(t) for t in turns)
    current_tokens = len(current_text) // 4  # Rough estimate

    return current_tokens > threshold * token_budget


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses simple heuristic: ~4 characters per token for English.

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    return len(text) // 4


def compress_with_llm(
    turns: list[Turn],
    llm_summarize_fn: callable,
    token_budget: int = 2000,
    keep_recent_turns: int = 5,
) -> str:
    """Compress conversation using LLM for better summarization.

    Args:
        turns: List of conversation turns
        llm_summarize_fn: Function that takes text and returns summary
        token_budget: Maximum tokens allowed
        keep_recent_turns: Number of recent turns to keep verbatim

    Returns:
        Compressed conversation text
    """
    if not turns:
        return ""

    old_turns = turns[:-keep_recent_turns] if len(turns) > keep_recent_turns else []
    recent_turns = turns[-keep_recent_turns:]

    parts = []

    # Use LLM to summarize old turns
    if old_turns:
        old_text = "\n".join(_turn_to_text(t) for t in old_turns)
        summary = llm_summarize_fn(old_text)
        parts.append(f"[Summary of {len(old_turns)} turns]\n{summary}\n")

    # Add recent turns verbatim
    for turn in recent_turns:
        parts.append(_turn_to_text(turn))

    return "\n".join(parts)
