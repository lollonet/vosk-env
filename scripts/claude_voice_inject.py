#!/usr/bin/env python3
"""
Claude Voice Inject - Injection vocale per sessioni Claude attive
Connette al daemon esistente e injecta testo nel terminale corrente
"""

import asyncio
import websockets
import json
import sys
import os
import termios
import tty
import select
import threading
import queue
import time
import subprocess
from pathlib import Path

class VoiceInject:
    def __init__(self, server_url='ws://localhost:8765'):
        self.server_url = server_url
        self.websocket = None
        self.running = False
        self.voice_queue = queue.Queue()
        
        # Stati terminale
        self.old_settings = None
        
        # Correzioni sviluppo per Claude
        self.dev_corrections = {
            'paiton': 'python', 'giava script': 'javascript',
            'react': 'React', 'nod jes': 'nodejs', 'vue jes': 'Vue.js',
            'django': 'Django', 'flask': 'Flask', 'express': 'Express', 
            'mai sequel': 'MySQL', 'postgres': 'PostgreSQL', 'mongo db': 'MongoDB',
            'docher': 'Docker', 'kubernetes': 'Kubernetes', 'git': 'Git',
            'ei pi ai': 'API', 'rest': 'REST', 'graphql': 'GraphQL',
            'debug': 'debug', 'refactor': 'refactor', 'ottimizza': 'optimize',
            'spiega': 'explain', 'crea': 'create', 'implementa': 'implement',
            'claude aiuto': 'help me', 'claude crea': 'create', 'claude spiega': 'explain',
        }

    def correct_dev_text(self, text):
        """Correggi terminologia per sviluppo"""
        if not text.strip():
            return text
        
        corrected = text.lower()
        for wrong, correct in self.dev_corrections.items():
            corrected = corrected.replace(wrong, correct)
        
        # Capitalizza prima lettera
        corrected = corrected.strip()
        if corrected:
            corrected = corrected[0].upper() + corrected[1:] if len(corrected) > 1 else corrected.upper()
        
        return corrected

    async def connect_voice_server(self):
        """Connetti al daemon voice esistente"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print("🌐 Connesso al voice daemon")
            return True
        except Exception as e:
            print(f"❌ Voice daemon non disponibile: {e}")
            print("💡 Assicurati che sia attivo: ./voice_daemon.sh start")
            return False

    async def capture_voice_input(self, timeout=10):
        """Cattura input vocale dal daemon"""
        try:
            # Richiedi single capture
            await self.websocket.send(json.dumps({
                'type': 'start_single_capture'
            }))
            
            print("🎤 Parla ora...")
            start_time = asyncio.get_event_loop().time()
            
            async for message in self.websocket:
                data = json.loads(message)
                
                if data.get('type') == 'speech_result':
                    text = data.get('text', '').strip()
                    if text:
                        # Applica correzioni
                        corrected = self.correct_dev_text(text)
                        print(f"📝 Riconosciuto: '{corrected}'")
                        return corrected
                
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    print("⏰ Timeout voice input")
                    break
            
            return None
            
        except Exception as e:
            print(f"❌ Errore voice capture: {e}")
            return None

    def setup_terminal_raw(self):
        """Setup terminale per input diretto"""
        try:
            self.old_settings = termios.tcgetattr(sys.stdin)
            return True
        except:
            return False

    def restore_terminal(self):
        """Ripristina terminale"""
        if self.old_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
            except:
                pass

    def inject_text_to_terminal(self, text):
        """Inject testo nel terminale corrente"""
        try:
            # Metodo 1: Simula typing con subprocess
            subprocess.run(['xdotool', 'type', text], check=False, stderr=subprocess.DEVNULL)
            return True
        except:
            try:
                # Metodo 2: Scrive direttamente su stdout 
                sys.stdout.write(text)
                sys.stdout.flush()
                return True
            except:
                return False

    def setup_hotkey_listener(self):
        """Setup hotkey listener in background thread"""
        def hotkey_thread():
            try:
                if not self.setup_terminal_raw():
                    print("❌ Impossibile setup hotkey listener")
                    return
                
                print("⌨️  Hotkey attivo: Ctrl+V per voice input")
                print("⌨️  Hotkey attivo: Ctrl+Q per quit")
                
                while self.running:
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        char = sys.stdin.read(1)
                        
                        # Ctrl+V (ASCII 22)
                        if ord(char) == 22:
                            self.voice_queue.put('voice_request')
                        # Ctrl+Q (ASCII 17)  
                        elif ord(char) == 17:
                            self.voice_queue.put('quit')
                            break
                    
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"❌ Errore hotkey listener: {e}")
            finally:
                self.restore_terminal()
        
        # Avvia thread hotkey
        hotkey_thread_obj = threading.Thread(target=hotkey_thread, daemon=True)
        hotkey_thread_obj.start()
        return hotkey_thread_obj

    async def run_voice_injection(self):
        """Main loop voice injection"""
        if not await self.connect_voice_server():
            return False
        
        self.running = True
        print("\n🎤 Claude Voice Inject ATTIVO")
        print("=" * 40)
        print("💡 Hotkey:")
        print("  Ctrl+V = Voice input")
        print("  Ctrl+Q = Quit")
        print("=" * 40)
        
        # Setup hotkey listener
        hotkey_thread = self.setup_hotkey_listener()
        
        try:
            while self.running:
                try:
                    # Check per richieste voice
                    request = self.voice_queue.get(timeout=0.5)
                    
                    if request == 'voice_request':
                        print("\n🎤 Voice input attivato...")
                        
                        # Cattura voice
                        voice_text = await self.capture_voice_input()
                        
                        if voice_text:
                            print(f"💬 Testo da inserire: '{voice_text}'")
                            
                            # Conferma
                            confirm = input("📤 Inserire? [Y/n]: ").strip().lower()
                            if confirm in ['', 'y', 'yes', 'si', 's']:
                                # Inject nel terminale
                                if self.inject_text_to_terminal(voice_text):
                                    print("✅ Testo inserito")
                                else:
                                    print("❌ Errore injection, copia manualmente:")
                                    print(f"   {voice_text}")
                            else:
                                print("⏭️  Saltato")
                        else:
                            print("❌ Nessun input vocale ricevuto")
                    
                    elif request == 'quit':
                        break
                        
                except queue.Empty:
                    continue
                except KeyboardInterrupt:
                    break
        
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            print("\n👋 Voice injection terminato")
            return True

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Claude Voice Inject - Voice input per sessioni Claude attive')
    parser.add_argument('--server', default='ws://localhost:8765', help='URL voice server')
    parser.add_argument('--quick', '-q', action='store_true', help='Single voice capture')
    
    args = parser.parse_args()
    
    injector = VoiceInject(args.server)
    
    if args.quick:
        # Modalità quick: single capture
        if await injector.connect_voice_server():
            text = await injector.capture_voice_input()
            if text:
                print(f"Testo riconosciuto: {text}")
                # Inject direttamente
                if injector.inject_text_to_terminal(text):
                    print("✅ Testo inserito")
                else:
                    print("Copia manualmente:")
                    print(text)
            else:
                print("❌ Nessun input ricevuto")
    else:
        # Modalità continua con hotkey
        await injector.run_voice_injection()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Uscita")