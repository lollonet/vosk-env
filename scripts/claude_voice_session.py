#!/usr/bin/env python3
"""
Claude Voice Session - Voice input integrato in Claude Code
"""

import asyncio
import json
import queue
import re
import select
import signal
import subprocess
import sys
import termios
import tty

import websockets


class ClaudeVoiceSession:
    def __init__(self, server_url="ws://localhost:8765"):
        self.server_url = server_url
        self.websocket = None
        self.claude_process = None
        self.voice_active = False
        self.current_language = "it"
        self.input_queue = queue.Queue()
        self.voice_queue = queue.Queue()

        # Stati terminale
        self.old_settings = None
        self.running = True

        # Correzioni sviluppo
        self.dev_corrections = {
            "paiton": "python",
            "giava script": "javascript",
            "react": "React",
            "nod jes": "nodejs",
            "vue jes": "Vue.js",
            "django": "Django",
            "flask": "Flask",
            "express": "Express",
            "mai sequel": "MySQL",
            "postgres": "PostgreSQL",
            "mongo db": "MongoDB",
            "docher": "Docker",
            "kubernetes": "Kubernetes",
            "git": "Git",
            "ei pi ai": "API",
            "rest": "REST",
            "graphql": "GraphQL",
            "debug": "debug",
            "refactor": "refactor",
            "ottimizza": "optimize",
            "spiega": "explain",
            "crea": "create",
            "implementa": "implement",
        }

        # Template prompt Claude
        self.claude_templates = {
            "spiega": "Explain this code:",
            "debug": "Debug this error:",
            "ottimizza": "Optimize this code:",
            "refactor": "Refactor this code:",
            "crea funzione": "Create a function that:",
            "crea classe": "Create a class that:",
            "test": "Write tests for:",
            "documenta": "Document this code:",
            "review": "Review this code:",
            "fix": "Fix this bug:",
            "migliora": "Improve this code:",
        }

    async def connect_voice_server(self):
        """Connetti al voice server"""
        try:
            self.websocket = await websockets.connect(self.server_url)

            # Richiedi stato lingua
            await self.websocket.send(json.dumps({"type": "get_language_status"}))

            print("🌐 Voice server connesso")
            return True
        except Exception as e:
            print(f"❌ Voice server non disponibile: {e}")
            return False

    def setup_terminal(self):
        """Setup terminale per intercettare hotkey"""
        try:
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
            return True
        except (OSError, termios.error):
            return False

    def restore_terminal(self):
        """Ripristina terminale"""
        if self.old_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
            except (OSError, termios.error):
                pass

    def correct_voice_text(self, text):
        """Correggi testo voice per sviluppo"""
        if not text.strip():
            return text

        original = text
        corrected = text.lower()

        # Correzioni terminologia sviluppo
        for wrong, correct in self.dev_corrections.items():
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            corrected = pattern.sub(correct, corrected)

        # Espandi template
        for trigger, template in self.claude_templates.items():
            if corrected.startswith(trigger):
                remainder = corrected[len(trigger) :].strip()
                if remainder:
                    return f"{template} {remainder}"
                else:
                    return template

        if corrected != original.lower():
            print(f"\n🔧 Voice correction: '{original}' → '{corrected}'")

        return corrected

    async def handle_voice_messages(self):
        """Gestisce messaggi dal voice server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)

                if data.get("type") == "speech_result":
                    text = data.get("text", "").strip()
                    if text:
                        corrected = self.correct_voice_text(text)
                        self.voice_queue.put(corrected)

                elif data.get("type") == "language_switched":
                    self.current_language = data.get("language", "it")
                    lang_name = {"it": "🇮🇹 Italiano", "en": "🇺🇸 English"}
                    print(
                        f"\n🌍 Lingua: {lang_name.get(self.current_language, self.current_language)}"
                    )

                elif data.get("type") == "listening_started":
                    self.voice_active = True
                    print("\n🎤 Voice input ATTIVO - parla ora...")

                elif data.get("type") == "listening_stopped":
                    self.voice_active = False
                    print("\n🛑 Voice input disattivato")

        except websockets.exceptions.ConnectionClosed:
            print("\n🔌 Voice server disconnesso")
        except Exception as e:
            print(f"\n❌ Errore voice: {e}")

    async def toggle_voice_input(self):
        """Toggle voice input"""
        if not self.websocket:
            print("\n❌ Voice server non connesso")
            return

        try:
            if self.voice_active:
                await self.websocket.send(
                    json.dumps({"type": "stop_permanent_listening"})
                )
                print("\n🛑 Voice input disattivato")
            else:
                await self.websocket.send(
                    json.dumps({"type": "start_permanent_listening"})
                )
                print("\n🎤 Voice input attivato - parla ora...")
        except Exception as e:
            print(f"\n❌ Errore toggle voice: {e}")

    async def switch_language(self):
        """Switch lingua IT/EN"""
        if not self.websocket:
            print("\n❌ Voice server non connesso")
            return

        try:
            new_lang = "en" if self.current_language == "it" else "it"
            await self.websocket.send(
                json.dumps({"type": "switch_language", "language": new_lang})
            )
            print(
                f"\n🔄 Switching to {'English' if new_lang == 'en' else 'Italiano'}..."
            )
        except Exception as e:
            print(f"\n❌ Errore switch lingua: {e}")

    def detect_hotkeys(self, char):
        """Rileva hotkey Ctrl+/ e Ctrl+?"""
        # Ctrl+/ = ASCII 31 (0x1F)
        if ord(char) == 31:  # Ctrl+/
            return "toggle_voice"
        # Ctrl+? = Ctrl+Shift+/ = ASCII 127 (0x7F) o simile
        elif ord(char) == 127 or ord(char) == 63:  # Ctrl+?
            return "switch_language"
        return None

    async def keyboard_handler(self):
        """Gestisce input da tastiera e hotkey"""
        asyncio.get_event_loop()

        while self.running:
            try:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    char = sys.stdin.read(1)

                    # Rileva hotkey
                    hotkey = self.detect_hotkeys(char)

                    if hotkey == "toggle_voice":
                        await self.toggle_voice_input()
                        continue
                    elif hotkey == "switch_language":
                        await self.switch_language()
                        continue

                    # Input normale - invia a Claude
                    if self.claude_process and self.claude_process.stdin:
                        try:
                            self.claude_process.stdin.write(char)
                            self.claude_process.stdin.flush()
                        except (OSError, BrokenPipeError):
                            pass

                # Check voice input
                try:
                    voice_text = self.voice_queue.get_nowait()
                    if voice_text and self.claude_process and self.claude_process.stdin:
                        # Inserisci voice text come input
                        try:
                            self.claude_process.stdin.write(voice_text)
                            self.claude_process.stdin.flush()
                            print(
                                f"\n📝 Voice inserted: {voice_text[:50]}{'...' if len(voice_text) > 50 else ''}"
                            )
                        except (OSError, BrokenPipeError):
                            pass
                except queue.Empty:
                    pass

                await asyncio.sleep(0.01)

            except Exception as e:
                if self.running:
                    print(f"\n❌ Keyboard handler error: {e}")
                break

    async def start_claude_session(self, claude_args=None):
        """Avvia sessione Claude Code con voice integration"""

        # Comando Claude
        cmd = ["claude"]
        if claude_args:
            cmd.extend(claude_args)
        else:
            cmd.append("chat")

        print("🚀 Avvio Claude Code con Voice Integration...")
        print("⌨️  Hotkeys:")
        print("   Ctrl+/ = Toggle Voice Input")
        print("   Ctrl+? = Switch Language IT ↔ EN")
        print("   Ctrl+C = Exit")
        print()

        try:
            # Avvia Claude Code
            self.claude_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,
            )

            # Setup terminale
            if not self.setup_terminal():
                print("⚠️  Hotkey potrebbero non funzionare")

            # Avvia handler voice messages
            voice_task = asyncio.create_task(self.handle_voice_messages())

            # Avvia keyboard handler
            keyboard_task = asyncio.create_task(self.keyboard_handler())

            # Output handler per Claude
            async def output_handler():
                try:
                    while self.running and self.claude_process:
                        line = await loop.run_in_executor(
                            None, self.claude_process.stdout.readline
                        )
                        if line:
                            print(line, end="")
                        elif self.claude_process.poll() is not None:
                            break
                except Exception:
                    pass

            loop = asyncio.get_event_loop()
            output_task = asyncio.create_task(output_handler())

            # Attendi completamento
            await asyncio.gather(
                voice_task, keyboard_task, output_task, return_exceptions=True
            )

        except KeyboardInterrupt:
            print("\n🛑 Interruzione utente")
        except Exception as e:
            print(f"\n❌ Errore Claude session: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup risorse"""
        self.running = False

        # Chiudi Claude process
        if self.claude_process:
            try:
                self.claude_process.terminate()
                await asyncio.sleep(1)
                if self.claude_process.poll() is None:
                    self.claude_process.kill()
            except Exception:
                pass

        # Ripristina terminale
        self.restore_terminal()

        # Chiudi WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass

        print("\n👋 Claude Voice Session terminata")


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Claude Code con Voice Input Integrato"
    )
    parser.add_argument(
        "--computer-use", action="store_true", help="Avvia in modalità computer use"
    )
    parser.add_argument(
        "--chat", action="store_true", help="Avvia in modalità chat (default)"
    )
    parser.add_argument(
        "--server", default="ws://localhost:8765", help="URL voice server"
    )
    parser.add_argument(
        "claude_args", nargs="*", help="Argomenti aggiuntivi per Claude Code"
    )

    args = parser.parse_args()

    # Verifica Claude Code
    try:
        subprocess.run(["claude", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("❌ Claude Code non trovato")
        print("💡 Installa da: https://github.com/anthropics/claude-code")
        return

    # Determina argomenti Claude
    claude_args = list(args.claude_args) if args.claude_args else []

    if args.computer_use:
        claude_args = ["computer", "use"] + claude_args
    elif args.chat or not claude_args:
        claude_args = ["chat"] + claude_args

    # Avvia sessione
    session = ClaudeVoiceSession(args.server)

    if await session.connect_voice_server():
        try:
            await session.start_claude_session(claude_args)
        except KeyboardInterrupt:
            print("\n🛑 Terminazione...")
    else:
        print("❌ Impossibile connettersi al voice server")
        print("💡 Verifica: ./voice_daemon.sh start")


if __name__ == "__main__":
    # Gestione segnali
    def signal_handler(signum, frame):
        print(f"\n🛑 Segnale {signum} ricevuto")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    asyncio.run(main())
