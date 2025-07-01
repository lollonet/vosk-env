"""Tests for configuration management."""

from unittest.mock import patch

from src.vosk_voice_assistant.config import Settings, VoskConfig, WebSocketConfig


class TestVoskConfig:
    """Test VoskConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = VoskConfig()

        assert config.sample_rate == 16000
        assert config.verbose is False
        assert config.block_size == 8000
        assert config.channels == 1
        assert config.dtype == "int16"
        assert "it" in config.model_paths
        assert "en" in config.model_paths

    def test_custom_values(self):
        """Test custom configuration values."""
        config = VoskConfig(
            sample_rate=22050,
            verbose=True,
            block_size=4000,
        )

        assert config.sample_rate == 22050
        assert config.verbose is True
        assert config.block_size == 4000


class TestWebSocketConfig:
    """Test WebSocketConfig class."""

    def test_default_values(self):
        """Test default WebSocket configuration."""
        config = WebSocketConfig()

        assert config.host == "localhost"
        assert config.port == 8765
        assert config.max_size == 1024 * 1024

    def test_custom_values(self):
        """Test custom WebSocket configuration."""
        config = WebSocketConfig(
            host="0.0.0.0",
            port=9000,
            max_size=2048,
        )

        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.max_size == 2048


class TestSettings:
    """Test Settings class."""

    def test_default_settings(self):
        """Test default application settings."""
        settings = Settings()

        assert isinstance(settings.vosk, VoskConfig)
        assert isinstance(settings.websocket, WebSocketConfig)
        assert settings.log_level == "INFO"
        assert "%(asctime)s" in settings.log_format

    @patch.dict("os.environ", {"VOSK_LOG_LEVEL": "DEBUG"})
    def test_environment_variables(self):
        """Test settings from environment variables."""
        settings = Settings()
        assert settings.log_level == "DEBUG"

    @patch.dict("os.environ", {"VOSK_VOSK__SAMPLE_RATE": "22050"})
    def test_nested_environment_variables(self):
        """Test nested configuration from environment variables."""
        settings = Settings()
        assert settings.vosk.sample_rate == 22050
