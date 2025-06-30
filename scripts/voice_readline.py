#!/usr/bin/env python3
"""
Voice Readline Integration - Integra voice input con readline bash
"""

import asyncio
import websockets
import json
import readline
import sys
import os
import threading
import queue
import time

class VoiceReadline:
    def __init__(self, server_url='ws://localhost:8765'):
        self.server_url = server_url
        self.websocket = None
        self.voice_queue = queue.Queue()
        self.listening = False
        
    async def connect_voice_server(self):
        """Connetti al server voice"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            return True
        except:
            return False
    
    async def voice_listener(self):
        """Thread per ascoltare voice input"""
        if not self.websocket:
            return
            
        try:
            await self.websocket.send(json.dumps({
                'type': 'start_permanent_listening'
            }))
            
            async for message in self.websocket:
                data = json.loads(message)
                if data.get('type') == 'speech_result':
                    text = data.get('text', '').strip()
                    if text:
                        self.voice_queue.put(text)
        except:
            pass
    
    def voice_input_function(self, prompt):
        """Funzione di input che supporta voice"""
        print(f"{prompt}", end='', flush=True)
        
        # Avvia voice listener in thread separato
        def start_voice():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.voice_listener())
        
        voice_thread = threading.Thread(target=start_voice, daemon=True)
        voice_thread.start()
        
        # Input ibrido: tastiera o voice
        typed_text = ""
        cursor_pos = 0
        
        while True:
            # Check voice input
            try:
                voice_text = self.voice_queue.get_nowait()
                print(f"\n🎤 Voice: {voice_text}")
                choice = input("Usa voice input? (y/N): ")
                if choice.lower() == 'y':
                    return voice_text
            except queue.Empty:
                pass
            
            # Input normale con readline
            try:
                result = input("")
                return result
            except KeyboardInterrupt:
                return ""

# Installa hook readline
voice_readline = VoiceReadline()

async def setup_voice_readline():
    """Setup voice readline"""
    if await voice_readline.connect_voice_server():
        print("✅ Voice readline attivato")
        # Imposta funzione input personalizzata
        __builtins__['input'] = voice_readline.voice_input_function
    else:
        print("❌ Voice server non disponibile")

# Auto-setup se importato
if __name__ != "__main__":
    asyncio.run(setup_voice_readline())
