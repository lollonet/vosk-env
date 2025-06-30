"""Custom exceptions for Vosk Voice Assistant."""


class VoskVoiceAssistantError(Exception):
    """Base exception for Vosk Voice Assistant."""

    pass


class ModelNotFoundError(VoskVoiceAssistantError):
    """Raised when a Vosk model is not found."""

    pass


class AudioDeviceError(VoskVoiceAssistantError):
    """Raised when there's an issue with audio device."""

    pass


class WebSocketError(VoskVoiceAssistantError):
    """Raised when there's an issue with WebSocket connection."""

    pass


class ConfigurationError(VoskVoiceAssistantError):
    """Raised when there's a configuration issue."""

    pass
