"""
DeepSeek Reasoner Model Patch for LangChain

DeepSeek's reasoning model (deepseek-reasoner) returns a `reasoning_content` field
in assistant messages containing the model's chain-of-thought reasoning. The DeepSeek
API **requires** this field to be present in assistant messages when sending back
conversation history in multi-turn conversations.

LangChain's `langchain-openai` (as of v1.0.1) does not preserve `reasoning_content`
through its message conversion functions:
  - `_convert_dict_to_message()` drops it when parsing API responses
  - `_convert_message_to_dict()` doesn't serialize it back for API requests

This module monkey-patches both functions to preserve `reasoning_content` in
`AIMessage.additional_kwargs`, enabling seamless multi-turn conversations with
DeepSeek Reasoner through LangChain/LangGraph agents.

Usage:
    from tools.deepseek_reasoning_patch import apply_deepseek_reasoning_patch
    apply_deepseek_reasoning_patch()  # Call once at startup before any LLM calls
"""

import logging
from typing import Any, Mapping

logger = logging.getLogger(__name__)

_patch_applied = False


def apply_deepseek_reasoning_patch() -> None:
    """
    Monkey-patch langchain-openai's message conversion functions to preserve
    `reasoning_content` for DeepSeek Reasoner model compatibility.

    Safe to call multiple times (idempotent). Safe for non-DeepSeek models
    (the patch only activates when `reasoning_content` is present).
    """
    global _patch_applied
    if _patch_applied:
        return

    import langchain_openai.chat_models.base as lc_base
    from langchain_core.messages import AIMessage

    # Save originals
    _original_convert_dict_to_message = lc_base._convert_dict_to_message
    _original_convert_message_to_dict = lc_base._convert_message_to_dict

    def _patched_convert_dict_to_message(_dict: Mapping[str, Any]):
        """Preserve reasoning_content from DeepSeek API response into AIMessage.additional_kwargs."""
        msg = _original_convert_dict_to_message(_dict)
        if isinstance(msg, AIMessage):
            reasoning_content = _dict.get("reasoning_content")
            if reasoning_content is not None:
                msg.additional_kwargs["reasoning_content"] = reasoning_content
        return msg

    # Maximum chars for reasoning_content in outgoing requests.
    # DeepSeek Reasoner can produce 50K-100K+ char reasoning chains; including
    # the full chain in every subsequent turn causes HTTP 413 from DeepSeek's proxy.
    # We truncate to keep useful context while staying within request size limits.
    REASONING_CONTENT_MAX_CHARS = 2000

    def _patched_convert_message_to_dict(message, *args, **kwargs):
        """Include (truncated) reasoning_content in API request payload for DeepSeek Reasoner."""
        result = _original_convert_message_to_dict(message, *args, **kwargs)
        if isinstance(message, AIMessage):
            reasoning_content = message.additional_kwargs.get("reasoning_content")
            if reasoning_content is not None:
                if len(reasoning_content) > REASONING_CONTENT_MAX_CHARS:
                    truncated = reasoning_content[:REASONING_CONTENT_MAX_CHARS]
                    logger.debug(
                        f"Truncating reasoning_content from {len(reasoning_content):,} "
                        f"to {REASONING_CONTENT_MAX_CHARS:,} chars to prevent HTTP 413"
                    )
                    result["reasoning_content"] = truncated
                else:
                    result["reasoning_content"] = reasoning_content
        return result

    # Apply patches
    lc_base._convert_dict_to_message = _patched_convert_dict_to_message
    lc_base._convert_message_to_dict = _patched_convert_message_to_dict

    _patch_applied = True
    logger.info("✅ DeepSeek reasoning_content patch applied to langchain-openai")
    print("✅ DeepSeek reasoning_content patch applied to langchain-openai")


def extract_reasoning_content(response: dict) -> str | None:
    """
    Extract reasoning_content from the final AI message in a LangGraph response.

    Args:
        response: The response dict from agent.ainvoke(), containing a 'messages' key.

    Returns:
        The reasoning_content string if found, or None.
    """
    messages = response.get("messages", []) if isinstance(response, dict) else []

    # Walk backwards to find the last AI message with reasoning_content
    for msg in reversed(messages):
        additional_kwargs = (
            msg.get("additional_kwargs", {})
            if isinstance(msg, dict)
            else getattr(msg, "additional_kwargs", {})
        )
        if additional_kwargs and additional_kwargs.get("reasoning_content"):
            return additional_kwargs["reasoning_content"]

    return None
