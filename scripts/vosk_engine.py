#!/usr/bin/env python3
"""
Vosk Speech Recognition Engine
Core per riconoscimento vocale real-time
"""

import json
import sys
import queue
import threading
import time
from pathlib import Path
import sounddevice as sd
import vosk

class VoskEngine:
    def __init__(self, model_path, sample_rate=16000, verbose=False):
        self.sample_rate = sample_rate
        self.verbose = verbose
        self.q = queue.Queue()
        self.is_listening = False
        
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
        
    def audio_callback(self, indata, frames, time, status):
        """Callback audio stream"""
        if status:
            print(f"⚠️  Audio warning: {status}", file=sys.stderr)
        self.q.put(bytes(indata))
    
    def start_listening(self, callback=None, duration=None):
        """
        Avvia listening continuo
        callback: funzione chiamata per ogni riconoscimento
        duration: durata in secondi (None = infinito)
        """
        self.is_listening = True
        start_time = time.time()
        
        try:
            device_info = sd.query_devices(kind='input')
            print(f"🎤 Dispositivo audio: {device_info['name']}")
            print(f"📡 Sample rate: {self.sample_rate}Hz")
            
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=8000,
                dtype='int16',
                channels=1,
                callback=self.audio_callback
            ):
                print("🔊 Listening attivo... (Ctrl+C per stop)")
                if duration:
                    print(f"⏱️  Durata: {duration} secondi")
                
                while self.is_listening:
                    # Check durata
                    if duration and (time.time() - start_time) > duration:
                        break
                        
                    try:
                        data = self.q.get(timeout=0.1)
                        
                        if self.rec.AcceptWaveform(data):
                            result = json.loads(self.rec.Result())
                            text = result.get('text', '').strip()
                            
                            if text:
                                confidence = result.get('confidence', 0)
                                if self.verbose:
                                    print(f"📝 [{confidence:.2f}] {text}")
                                
                                if callback:
                                    callback(text, confidence)
                                else:
                                    print(f"🗣️  {text}")
                                    
                    except queue.Empty:
                        continue
                        
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user")
        except Exception as e:
            print(f"❌ Errore: {e}")
        finally:
            self.is_listening = False
            
            # Final result se disponibile
            final_result = json.loads(self.rec.FinalResult())
            final_text = final_result.get('text', '').strip()
            if final_text:
                print(f"🎯 Final: {final_text}")
    
    def stop_listening(self):
        """Ferma listening"""
        self.is_listening = False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Vosk Speech Recognition Test')
    parser.add_argument('--model', 
                       default=f"{Path.home()}/vosk-env/models/italian",
                       help='Path modello Vosk')
    parser.add_argument('--lang', choices=['it', 'en'], default='it',
                       help='Lingua (it=italiano, en=inglese)')
    parser.add_argument('--duration', type=int,
                       help='Durata ascolto in secondi')
    parser.add_argument('--verbose', action='store_true',
                       help='Output dettagliato')
    
    args = parser.parse_args()
    
    # Seleziona modello
    if args.lang == 'en':
        model_path = f"{Path.home()}/vosk-env/models/english"
    else:
        model_path = f"{Path.home()}/vosk-env/models/italian"
    
    try:
        engine = VoskEngine(model_path, verbose=args.verbose)
        engine.start_listening(duration=args.duration)
    except Exception as e:
        print(f"❌ Errore inizializzazione: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
