#!/usr/bin/env python3
# voice-cli.py - Converte voce in comandi bash

import sys
import subprocess
from vosk_engine import VoskEngine
from pathlib import Path

class VoiceCLI:
    def __init__(self):
        model_path = f"{Path.home()}/.vosk/models/italian"
        self.engine = VoskEngine(model_path)
        
        # Mapping comandi vocali → bash
        self.command_map = {
            "lista file": "ls -la",
            "directory corrente": "pwd", 
            "spazio disco": "df -h",
            "processi attivi": "ps aux",
            "memoria": "free -h",
            "vai su": "cd ..",
            "pulisci schermo": "clear",
            "data": "date",
            "utente": "whoami"
        }
    
    def process_voice_command(self, text):
        """Processa comando vocale e esegue bash"""
        text = text.lower().strip()
        
        # Check comandi predefiniti
        if text in self.command_map:
            cmd = self.command_map[text]
            print(f"Executing: {cmd}")
            subprocess.run(cmd, shell=True)
            return
        
        # Comandi dinamici
        if text.startswith("vai in"):
            directory = text.replace("vai in", "").strip()
            subprocess.run(f"cd {directory}", shell=True)
        elif text.startswith("cerca"):
            query = text.replace("cerca", "").strip()
            subprocess.run(f"find . -name '*{query}*'", shell=True)
        else:
            print(f"Comando non riconosciuto: {text}")
    
    def start(self):
        print("Voice CLI attivo. Comandi disponibili:")
        for voice_cmd in self.command_map.keys():
            print(f"  '{voice_cmd}'")
        print()
        
        self.engine.start_listening(callback=self.process_voice_command)

if __name__ == "__main__":
    cli = VoiceCLI()
    cli.start()
