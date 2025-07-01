"""Tests for VoskEngine."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.vosk_voice_assistant.config import VoskConfig
from src.vosk_voice_assistant.engine import VoskEngine
from src.vosk_voice_assistant.exceptions import AudioDeviceError, ModelNotFoundError


class TestVoskEngine:
    """Test VoskEngine class."""

    @pytest.fixture
    def mock_model_path(self):
        """Create a temporary mock model directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_config(self, mock_model_path):
        """Create a mock configuration."""
        return VoskConfig(
            model_paths={"it": mock_model_path, "en": mock_model_path},
            verbose=False,
        )

    @patch("src.vosk_voice_assistant.engine.vosk")
    @patch("src.vosk_voice_assistant.engine.sd")
    def test_engine_initialization_success(
        self, mock_sd, mock_vosk, mock_config, mock_model_path
    ):
        """Test successful engine initialization."""
        mock_vosk.Model.return_value = Mock()
        mock_vosk.KaldiRecognizer.return_value = Mock()
        mock_sd.query_devices.return_value = {"name": "Test Device"}

        engine = VoskEngine(
            model_path=mock_model_path,
            language="it",
            config=mock_config,
        )

        assert engine.model_path == mock_model_path
        assert engine.language == "it"
        assert engine.config == mock_config
        assert not engine.is_listening
        mock_vosk.Model.assert_called_once_with(str(mock_model_path))

    def test_engine_initialization_model_not_found(self, mock_config):
        """Test engine initialization with non-existent model."""
        non_existent_path = Path("/non/existent/path")

        with pytest.raises(ModelNotFoundError):
            VoskEngine(
                model_path=non_existent_path,
                language="it",
                config=mock_config,
            )

    @patch("src.vosk_voice_assistant.engine.vosk")
    @patch("src.vosk_voice_assistant.engine.sd")
    def test_engine_initialization_model_load_failure(
        self, mock_sd, mock_vosk, mock_config, mock_model_path
    ):
        """Test engine initialization when Vosk model loading fails."""
        mock_vosk.Model.side_effect = Exception("Model load error")
        mock_sd.query_devices.return_value = {"name": "Test Device"}

        with pytest.raises(ModelNotFoundError):
            VoskEngine(
                model_path=mock_model_path,
                language="it",
                config=mock_config,
            )

    @patch("src.vosk_voice_assistant.engine.vosk")
    @patch("src.vosk_voice_assistant.engine.sd")
    def test_audio_device_setup_failure(
        self, mock_sd, mock_vosk, mock_config, mock_model_path
    ):
        """Test audio device setup failure."""
        mock_vosk.Model.return_value = Mock()
        mock_vosk.KaldiRecognizer.return_value = Mock()
        mock_sd.query_devices.side_effect = Exception("Audio device error")

        with pytest.raises(AudioDeviceError):
            VoskEngine(
                model_path=mock_model_path,
                language="it",
                config=mock_config,
            )

    @patch("src.vosk_voice_assistant.engine.vosk")
    @patch("src.vosk_voice_assistant.engine.sd")
    def test_get_supported_languages(self, mock_sd, mock_vosk, mock_model_path):
        """Test getting supported languages."""
        mock_vosk.Model.return_value = Mock()
        mock_vosk.KaldiRecognizer.return_value = Mock()
        mock_sd.query_devices.return_value = {"name": "Test Device"}

        # Create another temp directory for English model
        en_model_path = Path(tempfile.mkdtemp())
        try:
            config = VoskConfig(
                model_paths={"it": mock_model_path, "en": en_model_path},
            )

            engine = VoskEngine(
                model_path=mock_model_path,
                language="it",
                config=config,
            )

            supported = engine.get_supported_languages()
            assert "it" in supported
            assert "en" in supported
        finally:
            shutil.rmtree(en_model_path)

    @patch("src.vosk_voice_assistant.engine.vosk")
    @patch("src.vosk_voice_assistant.engine.sd")
    def test_stop_listening(self, mock_sd, mock_vosk, mock_config, mock_model_path):
        """Test stopping speech recognition."""
        mock_vosk.Model.return_value = Mock()
        mock_vosk.KaldiRecognizer.return_value = Mock()
        mock_sd.query_devices.return_value = {"name": "Test Device"}

        engine = VoskEngine(
            model_path=mock_model_path,
            language="it",
            config=mock_config,
        )

        engine.is_listening = True
        engine.stop_listening()
        assert not engine.is_listening
