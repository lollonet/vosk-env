#!/usr/bin/env python3
"""
Voice CLI - Controllo vocale per terminale
"""

import os
import sys
import subprocess
import re
from pathlib import Path
from vosk_engine import VoskEngine

class VoiceCLI:
    def __init__(self, model_path):
        self.engine = VoskEngine(model_path, verbose=True)
        
        # Comandi base voce → bash
        self.commands = {
            # Navigazione
            "lista file": "ls -la",
            "lista": "ls",
            "directory corrente": "pwd",
            "vai su": "cd ..",
            "vai home": "cd ~",
            
            # Sistema
            "spazio disco": "df -h",
            "memoria": "free -h", 
            "processi": "ps aux | head -10",
            "data": "date",
            "utente": "whoami",
            "riavvia": "sudo reboot",
            
            # Utilità
            "pulisci": "clear",
            "storia": "history | tail -10",
            "network": "ip addr show",
            "uptime": "uptime",
        }
        
        # Pattern dinamici
        self.dynamic_patterns = [
            (r"vai (?:in|nella) (.+)", r"cd '\1'"),
            (r"cerca (.+)", r"find . -name '*\1*' -type f"),
            (r"trova (.+)", r"locate '\1'"),
            (r"crea directory (.+)", r"mkdir -p '\1'"),
            (r"rimuovi (.+)", r"rm -rf '\1'"),
            (r"copia (.+) in (.+)", r"cp '\1' '\2'"),
            (r"sposta (.+) in (.+)", r"mv '\1' '\2'"),
            (r"apri (.+)", r"xdg-open '\1'"),
            (r"edita (.+)", r"nano '\1'"),
        ]
    
    def process_command(self, text, confidence):
        """Processa comando vocale"""
        text = text.lower().strip()
        
        print(f"\n🎯 Comando riconosciuto: '{text}' (conf: {confidence:.2f})")
        
        # Comandi diretti
        if text in self.commands:
            cmd = self.commands[text]
            self.execute_command(cmd)
            return
        
        # Pattern dinamici
        for pattern, replacement in self.dynamic_patterns:
            match = re.match(pattern, text)
            if match:
                try:
                    cmd = re.sub(pattern, replacement, text)
                    self.execute_command(cmd)
                    return
                except Exception as e:
                    print(f"❌ Errore pattern: {e}")
        
        # Comando libero (experimental)
        if text.startswith("esegui "):
            cmd = text[7:]  # Rimuovi "esegui "
            print(f"⚠️  Comando libero: {cmd}")
            confirm = input("Confermi esecuzione? (y/N): ")
            if confirm.lower() == 'y':
                self.execute_command(cmd)
            return
        
        print(f"❓ Comando non riconosciuto: '{text}'")
        self.show_help()
    
    def execute_command(self, cmd):
        """Esegui comando bash"""
        print(f"🚀 Eseguo: {cmd}")
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            if result.stdout:
                print("📤 Output:")
                print(result.stdout)
            
            if result.stderr:
                print("⚠️  Errori:")
                print(result.stderr)
                
            if result.returncode != 0:
                print(f"❌ Exit code: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            print("⏰ Timeout comando")
        except Exception as e:
            print(f"❌ Errore esecuzione: {e}")
    
    def show_help(self):
        """Mostra comandi disponibili"""
        print("\n📚 Comandi disponibili:")
        print("Comandi diretti:")
        for voice_cmd in sorted(self.commands.keys()):
            print(f"  • '{voice_cmd}'")
        
        print("\nPattern dinamici:")
        patterns = [
            "vai in <directory>",
            "cerca <filename>", 
            "crea directory <nome>",
            "rimuovi <file>",
            "copia <file> in <dest>",
            "apri <file>",
            "esegui <comando>"
        ]
        for pattern in patterns:
            print(f"  • {pattern}")
        print()
    
    def start(self):
        """Avvia voice CLI"""
        print("🎤 Voice CLI Attivo")
        print("==================")
        self.show_help()
        
        print("Inizia a parlare...")
        self.engine.start_listening(callback=self.process_command)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Voice CLI Controller')
    parser.add_argument('--model',
                       default=f"{Path.home()}/vosk-env/models/italian",
                       help='Path modello Vosk')
    parser.add_argument('--lang', choices=['it', 'en'], default='it')
    
    args = parser.parse_args()
    
    if args.lang == 'en':
        model_path = f"{Path.home()}/vosk-env/models/english"
    else:
        model_path = f"{Path.home()}/vosk-env/models/italian"
    
    try:
        cli = VoiceCLI(model_path)
        cli.start()
    except KeyboardInterrupt:
        print("\n👋 Arrivederci!")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    main()
