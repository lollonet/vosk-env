"""
Vosk Speech Recognition Engine

Core speech recognition functionality using Vosk with proper error handling,
logging, and type safety.
"""

import json
import queue
import time
from collections.abc import Callable
from pathlib import Path

import sounddevice as sd
import vosk

from .config import VoskConfig, settings
from .exceptions import AudioDeviceError, ModelNotFoundError
from .logging_config import get_logger

logger = get_logger(__name__)


class VoskEngine:
    """
    Speech recognition engine using Vosk.

    Provides real-time speech-to-text capabilities with configurable
    models, audio settings, and callback support.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        language: str = "it",
        config: VoskConfig | None = None,
    ) -> None:
        """
        Initialize Vosk engine.

        Args:
            model_path: Path to Vosk model directory
            language: Language code (it, en)
            config: Vosk configuration object

        Raises:
            ModelNotFoundError: If model path doesn't exist
            AudioDeviceError: If audio device configuration fails
        """
        self.config = config or settings.vosk
        self.language = language
        self.is_listening = False
        self.audio_queue: queue.Queue[bytes] = queue.Queue()

        # Determine model path
        if model_path:
            self.model_path = Path(model_path)
        else:
            self.model_path = self.config.model_paths.get(language)
            if not self.model_path:
                raise ModelNotFoundError(
                    f"No model configured for language: {language}"
                )

        # Validate model exists
        if not self.model_path.exists():
            raise ModelNotFoundError(f"Model not found: {self.model_path}")

        self._initialize_vosk()
        self._setup_audio_device()

        logger.info(f"VoskEngine initialized with model: {self.model_path.name}")

    def _initialize_vosk(self) -> None:
        """Initialize Vosk model and recognizer."""
        # Configure Vosk logging
        vosk.SetLogLevel(-1 if not self.config.verbose else 0)

        logger.info(f"Loading Vosk model: {self.model_path.name}")
        try:
            self.model = vosk.Model(str(self.model_path))
            self.recognizer = vosk.KaldiRecognizer(self.model, self.config.sample_rate)
            self.recognizer.SetWords(True)
            logger.info("Vosk model loaded successfully")
        except Exception as e:
            raise ModelNotFoundError(f"Failed to load Vosk model: {e}") from e

    def _setup_audio_device(self) -> None:
        """Setup audio device and validate configuration."""
        try:
            device_info = sd.query_devices(kind="input")
            logger.info(f"Audio device: {device_info['name']}")
            logger.info(f"Sample rate: {self.config.sample_rate}Hz")
        except Exception as e:
            raise AudioDeviceError(f"Failed to setup audio device: {e}") from e

    def _audio_callback(self, indata, frames, time, status) -> None:
        """Audio stream callback."""
        if status:
            logger.warning(f"Audio stream warning: {status}")
        self.audio_queue.put(bytes(indata))

    def start_listening(
        self,
        callback: Callable[[str, float], None] | None = None,
        duration: float | None = None,
    ) -> None:
        """
        Start continuous speech recognition.

        Args:
            callback: Function called for each recognition result (text, confidence)
            duration: Duration in seconds (None for infinite)

        Raises:
            AudioDeviceError: If audio stream fails to start
        """
        self.is_listening = True
        start_time = time.time()

        try:
            with sd.RawInputStream(
                samplerate=self.config.sample_rate,
                blocksize=self.config.block_size,
                dtype=self.config.dtype,
                channels=self.config.channels,
                callback=self._audio_callback,
            ):
                logger.info("Speech recognition started")
                if duration:
                    logger.info(f"Duration: {duration} seconds")

                while self.is_listening:
                    # Check duration limit
                    if duration and (time.time() - start_time) > duration:
                        logger.info("Duration limit reached")
                        break

                    try:
                        data = self.audio_queue.get(timeout=0.1)

                        if self.recognizer.AcceptWaveform(data):
                            result = self._process_recognition_result()
                            if result:
                                text, confidence = result
                                logger.debug(f"Recognition: [{confidence:.2f}] {text}")

                                if callback:
                                    callback(text, confidence)
                                else:
                                    logger.info(f"Recognized: {text}")

                    except queue.Empty:
                        continue

        except KeyboardInterrupt:
            logger.info("Speech recognition stopped by user")
        except Exception as e:
            raise AudioDeviceError(f"Audio stream error: {e}") from e
        finally:
            self._finalize_recognition(callback)

    def _process_recognition_result(self) -> tuple[str, float] | None:
        """Process recognition result from Vosk."""
        try:
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "").strip()
            confidence = result.get("confidence", 0.0)

            if text:
                return text, confidence

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to process recognition result: {e}")

        return None

    def _finalize_recognition(
        self, callback: Callable[[str, float], None] | None = None
    ) -> None:
        """Process final recognition result."""
        self.is_listening = False

        try:
            final_result = json.loads(self.recognizer.FinalResult())
            final_text = final_result.get("text", "").strip()

            if final_text:
                confidence = final_result.get("confidence", 0.0)
                logger.info(f"Final recognition: {final_text}")

                if callback:
                    callback(final_text, confidence)

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to process final result: {e}")

    def stop_listening(self) -> None:
        """Stop speech recognition."""
        logger.info("Stopping speech recognition")
        self.is_listening = False

    def get_supported_languages(self) -> list[str]:
        """Get list of supported languages based on available models."""
        return [lang for lang, path in self.config.model_paths.items() if path.exists()]
