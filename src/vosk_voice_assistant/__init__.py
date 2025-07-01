"""
Vosk Voice Assistant - A voice recognition system for Claude Code integration.

This package provides voice-to-text capabilities using Vosk engine with
support for browser integration and command-line interface.
"""

from .clients import ClaudeVoiceClient
from .config import settings
from .engine import VoskEngine
from .servers import VoiceWebSocketServer, start_voice_server
from .text_correction import correct_text

__version__ = "0.1.0"
__author__ = "Claudio Loletti"

__all__ = [
    "VoskEngine",
    "VoiceWebSocketServer",
    "start_voice_server",
    "ClaudeVoiceClient",
    "correct_text",
    "settings",
]
