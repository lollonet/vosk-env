#!/usr/bin/env python3
"""
Vosk Engine with Native Audio Capture - Shows mic icon in system tray
"""

import json
import queue
import sys
import time
from pathlib import Path

import vosk
from native_audio_capture import NativeAudioCapture


class VoskEngineNative:
    """Vosk engine using native audio capture that shows mic icon in tray"""
    
    def __init__(self, model_path, sample_rate=16000, verbose=False):
        self.sample_rate = sample_rate
        self.verbose = verbose
        self.q = queue.Queue()
        self.is_listening = False
        self.native_capture = None  # Create fresh for each capture session

        # Verifica modello
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Modello non trovato: {model_path}")

        # Configura Vosk
        vosk.SetLogLevel(-1 if not verbose else 0)

        print(f"🔄 Caricamento modello: {model_path.name}")
        self.model = vosk.Model(str(model_path))
        self.rec = vosk.KaldiRecognizer(self.model, sample_rate)
        self.rec.SetWords(True)
        print("✅ Modello caricato")

    def start_listening(self, callback=None, duration=None):
        """
        Avvia listening con native capture (mostra icona microfono)
        """
        self.is_listening = True
        start_time = time.time()

        try:
            print(f"🎤 Using NATIVE audio capture (shows tray icon)")
            print(f"📡 Sample rate: {self.sample_rate}Hz")
            
            # Create fresh capture instance for each session
            self.native_capture = NativeAudioCapture(self.sample_rate)
            
            # Clear queue for fresh start
            while not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    break
            
            # Native capture callback
            def native_audio_callback(audio_data: bytes):
                if self.is_listening:
                    self.q.put(audio_data)
            
            # Start native capture (this shows mic icon!)
            capture_thread = self.native_capture.start_capture(
                native_audio_callback, 
                duration=duration
            )
            
            print("🔊 Listening attivo... (Ctrl+C per stop)")
            if duration:
                print(f"⏱️  Durata: {duration} secondi")

            # Process audio data from queue
            while self.is_listening:
                # Check duration
                if duration and (time.time() - start_time) > duration:
                    break

                try:
                    data = self.q.get(timeout=0.1)

                    if self.rec.AcceptWaveform(data):
                        result = json.loads(self.rec.Result())
                        text = result.get("text", "").strip()

                        if text:
                            confidence = result.get("confidence", 0)
                            if self.verbose:
                                print(f"📝 [{confidence:.2f}] {text}")

                            if callback:
                                callback(text, confidence)
                            else:
                                print(f"🗣️  {text}")
                    else:
                        # Check partial results
                        partial = json.loads(self.rec.PartialResult())
                        partial_text = partial.get("partial", "")
                        if partial_text and self.verbose:
                            print(f"🔍 Partial: '{partial_text}'")

                except queue.Empty:
                    continue
            
            # Wait for capture thread to finish
            if capture_thread:
                capture_thread.join(timeout=2)

        except KeyboardInterrupt:
            print("\n🛑 Stopped by user")
        except Exception as e:
            print(f"❌ Errore: {e}")
        finally:
            self.is_listening = False
            if self.native_capture:
                self.native_capture.stop_capture()

            # Final result se disponibile
            try:
                final_result = json.loads(self.rec.FinalResult())
                final_text = final_result.get("text", "").strip()
                if final_text:
                    print(f"🎯 Final: {final_text}")
            except:
                pass

    def stop_listening(self):
        """Ferma listening"""
        self.is_listening = False
        if self.native_capture:
            self.native_capture.stop_capture()
            self.native_capture = None


def main():
    """Test del nuovo engine nativo"""
    import argparse

    parser = argparse.ArgumentParser(description="Vosk Speech Recognition Test (Native)")
    parser.add_argument(
        "--model",
        default=f"{Path.home()}/vosk-env/models-small-backup/vosk-model-small-en-us-0.15",
        help="Path modello Vosk",
    )
    parser.add_argument("--duration", type=int, help="Durata ascolto in secondi")
    parser.add_argument("--verbose", action="store_true", help="Output dettagliato")

    args = parser.parse_args()

    try:
        print("🎤 Testing NATIVE Vosk Engine (with tray icon)")
        engine = VoskEngineNative(args.model, verbose=args.verbose)
        engine.start_listening(duration=args.duration)
    except Exception as e:
        print(f"❌ Errore inizializzazione: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()