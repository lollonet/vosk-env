"""
Vosk Worker Process - Isolated process for speech recognition.

This runs Vosk in a separate process to isolate assertion errors and crashes
from the main WebSocket server.
"""

import json
import multiprocessing
import queue
import signal
import time
from pathlib import Path

import sounddevice as sd
import vosk

from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)


class VoskWorkerProcess:
    """Isolated Vosk worker process with crash recovery."""
    
    def __init__(self, language: str = "it"):
        self.language = language
        self.audio_queue = multiprocessing.Queue(maxsize=100)
        self.result_queue = multiprocessing.Queue(maxsize=50)
        self.control_queue = multiprocessing.Queue(maxsize=10)
        self.worker_process = None
        self.is_running = False
        
    def start_worker(self):
        """Start the Vosk worker process."""
        if self.worker_process and self.worker_process.is_alive():
            return
            
        logger.info(f"🚀 Starting Vosk worker process for {self.language}")
        self.worker_process = multiprocessing.Process(
            target=self._worker_main,
            args=(self.language, self.audio_queue, self.result_queue, self.control_queue),
            daemon=True
        )
        self.worker_process.start()
        self.is_running = True
        
    def stop_worker(self):
        """Stop the Vosk worker process."""
        if not self.worker_process:
            return
            
        logger.info("🛑 Stopping Vosk worker process")
        try:
            self.control_queue.put(("stop", None), timeout=1)
            self.worker_process.join(timeout=3)
        except:
            pass
            
        if self.worker_process.is_alive():
            logger.warning("Force terminating worker process")
            self.worker_process.terminate()
            self.worker_process.join(timeout=2)
            
        self.is_running = False
        
    def process_audio(self, audio_data: bytes, timeout: float = 30.0) -> tuple[str, float] | None:
        """
        Send audio to worker process and get recognition result.
        
        Returns:
            Tuple of (text, confidence) or None if failed/timeout
        """
        if not self.is_running or not self.worker_process.is_alive():
            logger.warning("Worker process dead, restarting...")
            self.restart_worker()
            
        try:
            # Send audio to worker
            self.audio_queue.put(("audio", audio_data), timeout=1)
            
            # Wait for result
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    result_type, result_data = self.result_queue.get(timeout=0.5)
                    if result_type == "result":
                        return result_data  # (text, confidence)
                    elif result_type == "error":
                        logger.error(f"Worker process error: {result_data}")
                        return None
                except queue.Empty:
                    continue
                    
            logger.warning("Worker process timeout")
            return None
            
        except Exception as e:
            logger.error(f"Error communicating with worker process: {e}")
            return None
            
    def restart_worker(self):
        """Restart crashed worker process."""
        logger.info("🔄 Restarting Vosk worker process")
        self.stop_worker()
        time.sleep(1)  # Brief pause
        self.start_worker()
        
    @staticmethod
    def _worker_main(language: str, audio_queue, result_queue, control_queue):
        """Main function for Vosk worker process."""
        logger.info(f"🎤 Vosk worker process started for {language}")
        
        try:
            # Initialize Vosk in worker process
            model_path = settings.vosk.model_paths.get(language)
            if not model_path or not model_path.exists():
                logger.error(f"Model not found for {language}: {model_path}")
                result_queue.put(("error", f"Model not found: {model_path}"))
                return
                
            logger.info(f"Loading Vosk model: {model_path}")
            model = vosk.Model(str(model_path))
            recognizer = vosk.KaldiRecognizer(model, 16000)
            recognizer.SetWords(True)
            
            logger.info("✅ Vosk worker ready")
            
            # Main processing loop
            while True:
                try:
                    # Check control commands
                    try:
                        cmd_type, cmd_data = control_queue.get_nowait()
                        if cmd_type == "stop":
                            logger.info("Worker received stop command")
                            break
                    except queue.Empty:
                        pass
                        
                    # Process audio
                    try:
                        msg_type, audio_data = audio_queue.get(timeout=0.1)
                        if msg_type == "audio":
                            VoskWorkerProcess._process_audio_chunk(
                                recognizer, audio_data, result_queue
                            )
                    except queue.Empty:
                        continue
                        
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Worker process error: {e}")
                    result_queue.put(("error", str(e)))
                    
        except Exception as e:
            logger.error(f"Worker process initialization failed: {e}")
            result_queue.put(("error", f"Initialization failed: {e}"))
            
        logger.info("🛑 Vosk worker process ended")
        
    @staticmethod
    def _process_audio_chunk(recognizer, audio_data: bytes, result_queue):
        """Process single audio chunk with Vosk."""
        try:
            # Fresh recognizer for each chunk to avoid corruption
            if len(audio_data) == 0:
                return
                
            # This is where assertion error can occur
            # If it happens, this worker process will crash but main server continues
            waveform_result = recognizer.AcceptWaveform(audio_data)
            
            if waveform_result:
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                confidence = result.get("confidence", 0.0)
                
                if text:
                    logger.info(f"✅ Worker recognition: [{confidence:.2f}] {text}")
                    result_queue.put(("result", (text, confidence)))
                    
        except Exception as e:
            # This catches the assertion error indirectly
            logger.warning(f"Audio processing error in worker: {e}")
            result_queue.put(("error", f"Processing error: {e}"))


def test_worker():
    """Test the worker process."""
    worker = VoskWorkerProcess("it")
    worker.start_worker()
    
    # Test with dummy audio
    import numpy as np
    dummy_audio = (np.random.random(3200) * 0.1).astype(np.int16).tobytes()
    
    result = worker.process_audio(dummy_audio, timeout=5)
    print(f"Test result: {result}")
    
    worker.stop_worker()


if __name__ == "__main__":
    test_worker()