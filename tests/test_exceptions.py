"""Tests for custom exceptions."""


from src.vosk_voice_assistant.exceptions import (
    AudioDeviceError,
    ConfigurationError,
    ModelNotFoundError,
    VoskVoiceAssistantError,
    WebSocketError,
)


class TestExceptions:
    """Test custom exception classes."""

    def test_base_exception(self):
        """Test base exception."""
        exc = VoskVoiceAssistantError("Base error")
        assert str(exc) == "Base error"
        assert isinstance(exc, Exception)

    def test_model_not_found_error(self):
        """Test ModelNotFoundError."""
        exc = ModelNotFoundError("Model not found")
        assert str(exc) == "Model not found"
        assert isinstance(exc, VoskVoiceAssistantError)

    def test_audio_device_error(self):
        """Test AudioDeviceError."""
        exc = AudioDeviceError("Audio device error")
        assert str(exc) == "Audio device error"
        assert isinstance(exc, VoskVoiceAssistantError)

    def test_websocket_error(self):
        """Test WebSocketError."""
        exc = WebSocketError("WebSocket error")
        assert str(exc) == "WebSocket error"
        assert isinstance(exc, VoskVoiceAssistantError)

    def test_configuration_error(self):
        """Test ConfigurationError."""
        exc = ConfigurationError("Configuration error")
        assert str(exc) == "Configuration error"
        assert isinstance(exc, VoskVoiceAssistantError)
