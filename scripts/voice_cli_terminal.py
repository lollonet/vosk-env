#!/usr/bin/env python3
"""
Voice CLI Terminal - Client per voice input nel terminale
"""

import asyncio
import json
import re
import subprocess

import websockets

# Dizionario correzioni comandi Linux
LINUX_COMMANDS = {
    # Comandi base
    "elle es": "ls",
    "liste": "ls",
    "lista": "ls",
    "list": "ls",
    "liste la": "ls -la",
    "liste tutto": "ls -la",
    "ci di": "cd",
    "vai in": "cd",
    "vai nella": "cd",
    "cartella": "cd",
    "directory": "cd",
    "pi uadiblu": "pwd",
    "dove sono": "pwd",
    "posizione": "pwd",
    "cartella corrente": "pwd",
    # File operations
    "tocca": "touch",
    "crea file": "touch",
    "nuovo file": "touch",
    "mkdir": "mkdir",
    "crea cartella": "mkdir",
    "nuova cartella": "mkdir",
    "copia": "cp",
    "sposta": "mv",
    "rimuovi": "rm",
    "cancella": "rm",
    "elimina": "rm",
    "rimuovi ricorsivo": "rm -rf",
    "cancella tutto": "rm -rf",
    "cat": "cat",
    "mostra": "cat",
    "visualizza": "cat",
    "leggi": "cat",
    "head": "head",
    "tail": "tail",
    "grep": "grep",
    "cerca": "grep",
    "trova": "find",
    "find": "find",
    # Permissions
    "chmod": "chmod",
    "permessi": "chmod",
    "chown": "chown",
    "proprietario": "chown",
    # Process management
    "pi es": "ps",
    "processi": "ps aux",
    "top": "top",
    "htop": "htop",
    "kill": "kill",
    "ammazza": "kill",
    "killall": "killall",
    "jobs": "jobs",
    "lavori": "jobs",
    "nohup": "nohup",
    "background": "bg",
    "foreground": "fg",
    # System info
    "df": "df -h",
    "spazio disco": "df -h",
    "du": "du -h",
    "dimensione": "du -h",
    "free": "free -h",
    "memoria": "free -h",
    "uptime": "uptime",
    "uname": "uname -a",
    "sistema": "uname -a",
    "whoami": "whoami",
    "chi sono": "whoami",
    "users": "users",
    "utenti": "users",
    "who": "who",
    "w": "w",
    # Network
    "ping": "ping",
    "pingi": "ping",
    "wget": "wget",
    "curl": "curl",
    "ssh": "ssh",
    "scp": "scp",
    "rsync": "rsync",
    "netstat": "netstat",
    "rete": "netstat",
    "porte": "netstat -tulpn",
    # Archive
    "tar": "tar",
    "archivio": "tar",
    "zip": "zip",
    "unzip": "unzip",
    "gzip": "gzip",
    "gunzip": "gunzip",
    # Text editors
    "nano": "nano",
    "vim": "vim",
    "vi": "vi",
    "emacs": "emacs",
    "gedit": "gedit",
    "edita": "nano",
    "modifica": "nano",
    # Package management (Ubuntu/Debian)
    "apt": "apt",
    "apt install": "sudo apt install",
    "installa": "sudo apt install",
    "apt update": "sudo apt update",
    "aggiorna": "sudo apt update",
    "apt upgrade": "sudo apt upgrade",
    "apt remove": "sudo apt remove",
    "rimuovi programma": "sudo apt remove",
    "apt search": "apt search",
    "cerca programma": "apt search",
    # Git commands
    "git": "git",
    "git status": "git status",
    "stato git": "git status",
    "git add": "git add",
    "aggiungi git": "git add",
    "git commit": "git commit",
    "commit": "git commit",
    "git push": "git push",
    "pus": "git push",
    "git pull": "git pull",
    "pul": "git pull",
    "git clone": "git clone",
    "clona": "git clone",
    "git log": "git log",
    "log git": "git log",
    "git diff": "git diff",
    "differenze": "git diff",
    # Docker
    "docker": "docker",
    "docker ps": "docker ps",
    "container": "docker ps",
    "docker images": "docker images",
    "immagini": "docker images",
    "docker run": "docker run",
    "esegui container": "docker run",
    "docker stop": "docker stop",
    "ferma container": "docker stop",
    "docker build": "docker build",
    "costruisci": "docker build",
    # System control
    "sudo": "sudo",
    "su": "su",
    "systemctl": "systemctl",
    "servizio": "systemctl",
    "service": "service",
    "reboot": "sudo reboot",
    "riavvia": "sudo reboot",
    "shutdown": "sudo shutdown",
    "spegni": "sudo shutdown -h now",
    "logout": "logout",
    "exit": "exit",
    "esci": "exit",
    "quit": "exit",
    # History and aliases
    "history": "history",
    "cronologia": "history",
    "alias": "alias",
    "which": "which",
    "dove": "which",
    "type": "type",
    "man": "man",
    "manuale": "man",
    "help": "help",
    "aiuto": "help",
    # Environment
    "env": "env",
    "ambiente": "env",
    "export": "export",
    "esporta": "export",
    "echo": "echo",
    "stampa": "echo",
    "source": "source",
    "carica": "source",
}

# Pattern per comandi dinamici
COMMAND_PATTERNS = [
    (r"vai in (.+)", r"cd \1"),
    (r"vai nella (.+)", r"cd \1"),
    (r"crea file (.+)", r"touch \1"),
    (r"crea cartella (.+)", r"mkdir \1"),
    (r"copia (.+) in (.+)", r"cp \1 \2"),
    (r"sposta (.+) in (.+)", r"mv \1 \2"),
    (r"rimuovi (.+)", r"rm \1"),
    (r"cancella (.+)", r"rm \1"),
    (r"mostra (.+)", r"cat \1"),
    (r"edita (.+)", r"nano \1"),
    (r"cerca (.+)", r"grep \1"),
    (r"trova (.+)", r'find . -name "*\1*"'),
    (r"installa (.+)", r"sudo apt install \1"),
    (r"cerca programma (.+)", r"apt search \1"),
    (r"git aggiungi (.+)", r"git add \1"),
    (r"git commit (.+)", r'git commit -m "\1"'),
    (r"pingi (.+)", r"ping \1"),
    (r"ssh (.+)", r"ssh \1"),
    (r"sudo (.+)", r"sudo \1"),
    (r"esegui (.+)", r"\1"),
]


def correct_linux_command(text):
    """Corregge comandi Linux dal testo riconosciuto"""
    if not text.strip():
        return text

    original_text = text
    corrected_text = text.lower().strip()

    # 1. Correzioni dirette dal dizionario
    for voice_cmd, real_cmd in LINUX_COMMANDS.items():
        if corrected_text == voice_cmd or corrected_text.startswith(voice_cmd + " "):
            # Sostituisci solo la parte iniziale
            remainder = corrected_text[len(voice_cmd) :].strip()
            corrected_text = real_cmd + (" " + remainder if remainder else "")
            break

    # 2. Pattern dinamici
    for pattern, replacement in COMMAND_PATTERNS:
        match = re.match(pattern, corrected_text)
        if match:
            corrected_text = re.sub(pattern, replacement, corrected_text)
            break

    # 3. Pulizia finale
    corrected_text = re.sub(r"\s+", " ", corrected_text).strip()

    if corrected_text != original_text.lower():
        print(f"\n🔧 Comando corretto: '{original_text}' → '{corrected_text}'")

    return corrected_text


class VoiceTerminalClient:
    def __init__(self, server_url="ws://localhost:8765"):
        self.server_url = server_url
        self.websocket = None
        self.running = False
        self.last_command = None

    async def connect(self):
        """Connetti al server WebSocket"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print("🌐 Connesso al voice server")
            return True
        except Exception as e:
            print(f"❌ Errore connessione: {e}")
            return False

    async def start_listening(self):
        """Avvia listening permanente"""
        if not self.websocket:
            print("❌ Non connesso al server")
            return

        try:
            # Richiedi inizio listening
            await self.websocket.send(json.dumps({"type": "start_permanent_listening"}))

            self.running = True
            print("🎤 Voice input ATTIVO nel terminale")
            print("💡 Pronuncia comandi Linux in italiano o inglese")
            print("🛑 Ctrl+C per uscire")

            # Ascolta messaggi
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)

        except KeyboardInterrupt:
            await self.stop_listening()
        except Exception as e:
            print(f"❌ Errore: {e}")

    async def handle_message(self, data):
        """Gestisci messaggi dal server"""
        if data.get("type") == "speech_result":
            text = data.get("text", "").strip()
            if text:
                # Correggi comando
                corrected_command = correct_linux_command(text)
                self.last_command = corrected_command

                print(f"\n🗣️  Riconosciuto: {corrected_command}")

                # Chiedi conferma per comandi pericolosi
                if self.is_dangerous_command(corrected_command):
                    confirm = input(
                        "⚠️  Comando potenzialmente pericoloso. Eseguire? (y/N): "
                    )
                    if confirm.lower() != "y":
                        print("❌ Comando annullato")
                        return

                # Chiedi se eseguire
                choice = (
                    input("💾 [Enter]=Esegui [e]=Edita [s]=Salta: ").strip().lower()
                )

                if choice == "e":
                    # Modalità edit
                    edited = input(f"✏️  Modifica comando: {corrected_command}\n> ")
                    if edited.strip():
                        corrected_command = edited.strip()

                if choice != "s":
                    self.execute_command(corrected_command)

    def is_dangerous_command(self, cmd):
        """Controlla se un comando è potenzialmente pericoloso"""
        dangerous_patterns = [
            r"rm\s+-rf\s+/",
            r"rm\s+-rf\s+\*",
            r"sudo\s+rm\s+-rf",
            r"dd\s+if=",
            r"mkfs\.",
            r"fdisk",
            r"shutdown",
            r"reboot",
            r"killall",
            r"chmod\s+777",
            r"chown.*root",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, cmd):
                return True
        return False

    def execute_command(self, command):
        """Esegui comando shell"""
        try:
            print(f"🚀 Eseguendo: {command}")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=False,  # Output diretto nel terminale
                text=True,
            )

            if result.returncode != 0:
                print(f"⚠️  Comando terminato con exit code: {result.returncode}")
            else:
                print("✅ Comando completato")

        except Exception as e:
            print(f"❌ Errore esecuzione: {e}")

    async def stop_listening(self):
        """Ferma listening"""
        self.running = False
        if self.websocket:
            try:
                await self.websocket.send(
                    json.dumps({"type": "stop_permanent_listening"})
                )
                await self.websocket.close()
                print("\n🛑 Voice input disattivato")
            except (websockets.exceptions.ConnectionClosed, ConnectionError):
                pass


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Voice Input per Terminale Linux")
    parser.add_argument(
        "--server", default="ws://localhost:8765", help="URL server WebSocket"
    )
    parser.add_argument("--test", action="store_true", help="Test correzioni comandi")

    args = parser.parse_args()

    if args.test:
        # Test correzioni
        test_commands = [
            "liste la",
            "vai in cartella documenti",
            "crea file test.txt",
            "installa git",
            "git aggiungi tutto",
            "sudo aggiorna sistema",
            "pingi google.com",
            "cerca errore nel log",
        ]

        print("🧪 Test correzioni comandi:")
        for cmd in test_commands:
            corrected = correct_linux_command(cmd)
            print(f"  '{cmd}' → '{corrected}'")
        return

    # Avvia client
    client = VoiceTerminalClient(args.server)

    if await client.connect():
        await client.start_listening()
    else:
        print("❌ Impossibile connettersi al voice server")
        print("💡 Assicurati che sia attivo: ./voice_daemon.sh start")


if __name__ == "__main__":
    asyncio.run(main())
