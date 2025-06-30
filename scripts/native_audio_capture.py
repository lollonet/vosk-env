#!/usr/bin/env python3
"""
Native audio capture module - Shows mic icon in system tray
Single responsibility: Capture audio using system tools (parecord/arecord)
"""

import subprocess
import threading
import queue
import time
import signal
from typing import Callable, Optional


class NativeAudioCapture:
    """
    Audio capture using native system tools that trigger tray icons
    """
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.process: Optional[subprocess.Popen] = None
        self.audio_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
    
    def start_capture(self, callback: Callable[[bytes], None], duration: Optional[int] = None):
        """
        Start audio capture using parecord (shows mic icon in tray)
        
        Args:
            callback: Function called with audio data chunks
            duration: Optional duration in seconds
        """
        if self.is_recording:
            raise RuntimeError("Already recording")
        
        # Ensure clean state for new capture
        self._cleanup()
        
        self.is_recording = True
        self._stop_event.clear()
        
        # Use parecord for PulseAudio (shows tray icon)
        cmd = [
            "parecord",
            f"--format=s16le",
            f"--rate={self.sample_rate}",
            f"--channels={self.channels}",
            "--raw"  # Output raw data to stdout
        ]
        
        try:
            print(f"🎤 Starting native audio capture ({self.sample_rate}Hz)")
            
            # Start parecord process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=None
            )
            
            # Start reading thread
            read_thread = threading.Thread(
                target=self._read_audio_data,
                args=(callback, duration),
                daemon=True
            )
            read_thread.start()
            
            return read_thread
            
        except Exception as e:
            self.is_recording = False
            raise RuntimeError(f"Failed to start audio capture: {e}")
    
    def _read_audio_data(self, callback: Callable[[bytes], None], duration: Optional[int]):
        """Read audio data from parecord and send to callback"""
        chunk_size = 3200  # 0.1 seconds at 16kHz, 16-bit, mono
        start_time = time.time()
        
        try:
            while self.is_recording and self.process:
                # Check duration limit
                if duration and (time.time() - start_time) > duration:
                    break
                
                # Check if stop requested
                if self._stop_event.is_set():
                    break
                
                # Read audio chunk
                try:
                    chunk = self.process.stdout.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Send to callback
                    callback(chunk)
                    
                except Exception as e:
                    print(f"⚠️ Error reading audio: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Audio reading error: {e}")
        finally:
            self._cleanup()
    
    def stop_capture(self):
        """Stop audio capture"""
        if not self.is_recording:
            return
        
        print("🛑 Stopping native audio capture")
        self.is_recording = False
        self._stop_event.set()
        self._cleanup()
    
    def _cleanup(self):
        """Clean up process and resources"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except Exception as e:
                print(f"⚠️ Cleanup error: {e}")
            finally:
                self.process = None
        
        self.is_recording = False
        # Reset stop event for next use
        self._stop_event.clear()


def test_native_capture():
    """Test the native audio capture"""
    print("🧪 Testing native audio capture...")
    
    capture = NativeAudioCapture()
    chunks_received = 0
    
    def audio_callback(data: bytes):
        nonlocal chunks_received
        chunks_received += 1
        if chunks_received % 10 == 0:  # Log every 10 chunks (1 second)
            print(f"📊 Received {chunks_received} audio chunks ({len(data)} bytes)")
    
    try:
        print("🎤 Recording for 5 seconds with NATIVE capture...")
        print("💡 You should see mic icon in system tray!")
        
        thread = capture.start_capture(audio_callback, duration=5)
        thread.join(timeout=7)  # Wait with timeout
        
        print(f"✅ Test completed. Received {chunks_received} audio chunks")
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        capture.stop_capture()


if __name__ == "__main__":
    test_native_capture()