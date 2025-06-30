#!/usr/bin/env python3
"""
Voice Global Hotkeys - Hotkey globali per voice input sistema
"""

import asyncio
import websockets
import json
import subprocess
import threading
import time
import os
from pathlib import Path

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("⚠️  Modulo 'keyboard' non disponibile")
    print("💡 Installa con: pip install keyboard")

class VoiceGlobalHotkeys:
    def __init__(self, server_url='ws://localhost:8765'):
        self.server_url = server_url
        self.websocket = None
        self.voice_active = False
        
    async def connect(self):
        """Connetti al server"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print("🌐 Connesso al voice server")
            return True
        except Exception as e:
            print(f"❌ Errore connessione: {e}")
            return False
    
    def toggle_voice_global(self):
        """Toggle voice input globale"""
        if not self.websocket:
            print("❌ Server non connesso")
            return
        
        if self.voice_active:
            self.stop_voice()
        else:
            self.start_voice()
    
    def start_voice(self):
        """Avvia voice input globale"""
        try:
            # Determina se siamo in terminale o GUI
            if os.environ.get('DISPLAY'):
                # GUI - usa zenity per input
                self.start_gui_voice()
            else:
                # Terminale - usa input diretto
                self.start_terminal_voice()
                
        except Exception as e:
            print(f"❌ Errore avvio voice: {e}")
    
    def start_gui_voice(self):
        """Voice input per applicazioni GUI"""
        def voice_thread():
            try:
                # Usa zenity per mostrare dialog
                subprocess.run([
                    'zenity', '--info', 
                    '--text=🎤 Voice Input attivo...\nParla ora!'
                ], timeout=1)
            except:
                pass
            
            # Avvia voice capture
            asyncio.run(self.capture_voice_gui())
        
        threading.Thread(target=voice_thread, daemon=True).start()
    
    def start_terminal_voice(self):
        """Voice input per terminale"""
        print("🎤 Voice input attivo nel terminale...")
        asyncio.create_task(self.capture_voice_terminal())
    
    async def capture_voice_gui(self):
        """Cattura voice per GUI"""
        try:
            await self.websocket.send(json.dumps({
                'type': 'start_single_capture'
            }))
            
            # Ascolta risultato
            async for message in self.websocket:
                data = json.loads(message)
                if data.get('type') == 'speech_result':
                    text = data.get('text', '').strip()
                    if text:
                        # Inserisci testo nell'applicazione attiva
                        self.insert_text_gui(text)
                        break
                        
        except Exception as e:
            print(f"❌ Errore capture GUI: {e}")
    
    async def capture_voice_terminal(self):
        """Cattura voice per terminale"""
        try:
            await self.websocket.send(json.dumps({
                'type': 'start_single_capture'
            }))
            
            async for message in self.websocket:
                data = json.loads(message)
                if data.get('type') == 'speech_result':
                    text = data.get('text', '').strip()
                    if text:
                        print(f"🗣️  Voice: {text}")
                        break
                        
        except Exception as e:
            print(f"❌ Errore capture terminal: {e}")
    
    def insert_text_gui(self, text):
        """Inserisci testo in applicazione GUI attiva"""
        try:
            # Usa xdotool per inserire testo
            subprocess.run(['xdotool', 'type', text], check=True)
        except subprocess.CalledProcessError:
            try:
                # Fallback: usa clipboard
                subprocess.run(['echo', text], stdout=subprocess.PIPE)
                subprocess.run(['xclip', '-selection', 'clipboard'], 
                             input=text.encode(), check=True)
                # Simula Ctrl+V
                subprocess.run(['xdotool', 'key', 'ctrl+v'], check=True)
            except:
                print(f"❌ Impossibile inserire testo: {text}")
    
    def stop_voice(self):
        """Ferma voice input"""
        self.voice_active = False
        print("🛑 Voice input disattivato")
    
    def setup_hotkeys(self):
        """Setup hotkey globali"""
        if not KEYBOARD_AVAILABLE:
            print("❌ Keyboard module non disponibile")
            return False
        
        try:
            # Ctrl+Alt+V per voice input globale
            keyboard.add_hotkey('ctrl+alt+v', self.toggle_voice_global)
            print("✅ Hotkey globali attivate:")
            print("   Ctrl+Alt+V = Voice input globale")
            return True
        except Exception as e:
            print(f"❌ Errore setup hotkeys: {e}")
            return False
    
    async def run(self):
        """Avvia servizio hotkeys"""
        if await self.connect():
            if self.setup_hotkeys():
                print("🎤 Voice Global Hotkeys attivo")
                print("🛑 Premi Ctrl+C per uscire")
                
                try:
                    # Mantieni vivo
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\n👋 Hotkeys disattivate")
            else:
                print("❌ Impossibile attivare hotkeys")
        else:
            print("❌ Impossibile connettersi al voice server")

async def main():
    hotkeys = VoiceGlobalHotkeys()
    await hotkeys.run()

if __name__ == "__main__":
    if os.geteuid() == 0:
        print("⚠️  Non eseguire come root")
        sys.exit(1)
    
    asyncio.run(main())
