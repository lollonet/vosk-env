"""Text correction utilities for voice input processing."""

import re
from typing import Literal, cast

from .config import settings


def correct_text(
    text: str, context: Literal["browser", "terminal"] = "browser"
) -> str:
    """
    Correct voice-to-text input based on context.
    
    Args:
        text: Raw text from voice recognition
        context: Context for correction ("browser" or "terminal")
        
    Returns:
        Corrected text string
    """
    if not text.strip():
        return text

    corrected_text = text.lower()

    if context == "browser" and settings.server.default_language == "it":
        corrected_text = _apply_tech_term_corrections(corrected_text)
    elif context == "terminal":
        corrected_text = _apply_linux_command_corrections(corrected_text)

    return corrected_text


def _apply_tech_term_corrections(text: str) -> str:
    """Apply Italian tech term corrections for browser context."""
    for wrong, correct in settings.text_correction.it_tech_terms.items():
        pattern = re.compile(re.escape(wrong), re.IGNORECASE)
        text = pattern.sub(correct, text)
    return text


def _apply_linux_command_corrections(text: str) -> str:
    """Apply Linux command corrections for terminal context."""
    for voice_cmd, real_cmd in settings.text_correction.linux_commands.items():
        if text == voice_cmd or text.startswith(voice_cmd + " "):
            remainder = text[len(voice_cmd):].strip()
            return f"{real_cmd} {remainder}".strip() if remainder else real_cmd
    return text


def get_available_corrections(context: Literal["browser", "terminal"]) -> dict[str, str]:
    """
    Get available corrections for a given context.
    
    Args:
        context: Context for corrections
        
    Returns:
        Dictionary of available corrections
    """
    if context == "browser":
        return settings.text_correction.it_tech_terms
    elif context == "terminal":
        return settings.text_correction.linux_commands
    return {}
