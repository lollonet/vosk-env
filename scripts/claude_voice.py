#!/usr/bin/env python3
"""
Claude Voice - Voice input per Claude Code
"""

import asyncio
import json
import os
import re
import subprocess

import websockets


class ClaudeVoice:
    def __init__(self, server_url="ws://localhost:8765"):
        self.server_url = server_url
        self.websocket = None
        self.session_context = []
        self.current_project = None

        # Template prompt comuni
        self.prompt_templates = {
            # Sviluppo
            "spiega codice": "Analyze and explain this code:",
            "debug errore": "Help me debug this error:",
            "ottimizza codice": "Optimize this code for better performance:",
            "refactor codice": "Refactor this code to make it cleaner:",
            "aggiungi commenti": "Add comprehensive comments to this code:",
            "test unitari": "Create unit tests for this code:",
            "documenta funzione": "Create documentation for this function:",
            # Architettura
            "progetta architettura": "Design the architecture for:",
            "pattern design": "Suggest design patterns for:",
            "best practices": "What are the best practices for:",
            "migliora performance": "How can I improve performance of:",
            # Debug specifici
            "errore python": "Help me fix this Python error:",
            "errore javascript": "Help me fix this JavaScript error:",
            "errore sql": "Help me fix this SQL error:",
            "errore docker": "Help me fix this Docker issue:",
            # Creazione codice
            "crea funzione": "Create a function that:",
            "crea classe": "Create a class that:",
            "crea script": "Create a script that:",
            "crea api": "Create an API endpoint that:",
            "crea query": "Create a SQL query that:",
            # Review
            "review codice": "Review this code for potential issues:",
            "sicurezza codice": "Review this code for security vulnerabilities:",
            "code review": "Perform a comprehensive code review:",
        }

        # Correzioni terminologia sviluppo
        self.dev_corrections = {
            # Linguaggi
            "paiton": "python",
            "python": "python",
            "giava script": "javascript",
            "javascript": "javascript",
            "java script": "javascript",
            "node jes": "nodejs",
            "react": "react",
            "riact": "react",
            "view jes": "vue.js",
            "angular": "angular",
            # Frameworks
            "django": "django",
            "flask": "flask",
            "express": "express",
            "fastify": "fastify",
            "spring boot": "spring boot",
            "laravel": "laravel",
            # Database
            "mai sequel": "mysql",
            "postgres": "postgresql",
            "mongo db": "mongodb",
            "redis": "redis",
            "elastic search": "elasticsearch",
            # Tools
            "git": "git",
            "docker": "docker",
            "kubernetes": "kubernetes",
            "jenkins": "jenkins",
            "github actions": "github actions",
            "terraform": "terraform",
            "ansible": "ansible",
            # Concetti
            "ei pi ai": "API",
            "rest": "REST",
            "graphql": "GraphQL",
            "microservizi": "microservices",
            "ci cd": "CI/CD",
            "devops": "DevOps",
            "cloud native": "cloud native",
            # Comandi Claude specifici
            "claude aiuto": "claude help",
            "claude chat": "claude chat",
            "claude computer use": "claude computer use",
            "claude crea": "claude create",
            "claude esegui": "claude run",
        }

    async def connect(self):
        """Connetti al voice server"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print("🌐 Connesso al voice server")
            return True
        except Exception as e:
            print(f"❌ Errore connessione voice server: {e}")
            return False

    def correct_dev_text(self, text):
        """Correggi terminologia sviluppo"""
        if not text.strip():
            return text

        original_text = text
        corrected_text = text.lower()

        # Correzioni terminologia
        for wrong, correct in self.dev_corrections.items():
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            corrected_text = pattern.sub(correct, corrected_text)

        # Pulisci spazi multipli
        corrected_text = re.sub(r"\s+", " ", corrected_text).strip()

        if corrected_text != original_text.lower():
            print(f"🔧 Correzione dev: '{original_text}' → '{corrected_text}'")

        return corrected_text

    def expand_prompt_template(self, text):
        """Espandi template prompt comuni"""
        text_lower = text.lower().strip()

        # Cerca template corrispondente
        for trigger, template in self.prompt_templates.items():
            if text_lower.startswith(trigger):
                remainder = text[len(trigger) :].strip()
                if remainder:
                    return f"{template} {remainder}"
                else:
                    return template

        return text

    async def capture_voice_input(self, timeout=15):
        """Cattura input vocale con timeout"""
        try:
            await self.websocket.send(json.dumps({"type": "start_single_capture"}))

            start_time = asyncio.get_event_loop().time()

            async for message in self.websocket:
                data = json.loads(message)

                if data.get("type") == "speech_result":
                    text = data.get("text", "").strip()
                    if text:
                        # Applica correzioni
                        corrected = self.correct_dev_text(text)
                        expanded = self.expand_prompt_template(corrected)
                        return expanded

                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    print("⏰ Timeout voice input")
                    break

            return None

        except Exception as e:
            print(f"❌ Errore voice capture: {e}")
            return None

    def detect_current_context(self):
        """Rileva contesto corrente (file, directory, git repo)"""
        context = {}

        # Directory corrente
        context["pwd"] = os.getcwd()

        # File nel directory
        try:
            files = [f for f in os.listdir(".") if os.path.isfile(f)]
            context["files"] = files[:10]  # Prime 10 file
        except OSError:
            context["files"] = []

        # Git repo info
        try:
            git_branch = (
                subprocess.check_output(
                    ["git", "branch", "--show-current"], stderr=subprocess.DEVNULL
                )
                .decode()
                .strip()
            )
            context["git_branch"] = git_branch
        except (subprocess.CalledProcessError, FileNotFoundError):
            context["git_branch"] = None

        # Linguaggio predominante
        extensions = {}
        for file in context["files"]:
            ext = os.path.splitext(file)[1]
            if ext:
                extensions[ext] = extensions.get(ext, 0) + 1

        if extensions:
            main_ext = max(extensions, key=extensions.get)
            context["main_language"] = self.extension_to_language(main_ext)

        return context

    def extension_to_language(self, ext):
        """Mappa estensione → linguaggio"""
        mapping = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".go": "Go",
            ".rs": "Rust",
            ".php": "PHP",
            ".rb": "Ruby",
            ".sh": "Bash",
            ".sql": "SQL",
            ".html": "HTML",
            ".css": "CSS",
            ".json": "JSON",
            ".yml": "YAML",
            ".yaml": "YAML",
            ".xml": "XML",
            ".md": "Markdown",
            ".txt": "Text",
        }
        return mapping.get(ext.lower(), "Unknown")

    def build_context_prompt(self, user_prompt, context):
        """Costruisci prompt con contesto"""
        context_parts = []

        if context.get("main_language"):
            context_parts.append(f"Working with {context['main_language']}")

        if context.get("git_branch"):
            context_parts.append(f"Git branch: {context['git_branch']}")

        if context.get("pwd"):
            context_parts.append(f"Directory: {os.path.basename(context['pwd'])}")

        if context_parts:
            context_str = " | ".join(context_parts)
            return f"[Context: {context_str}]\n\n{user_prompt}"

        return user_prompt

    async def run_claude_code(self, prompt, args=None):
        """Esegui Claude Code con prompt"""
        try:
            # Costruisci comando
            cmd = ["claude"]

            if args:
                cmd.extend(args)

            # Se è una chat, usa chat mode
            if not args or "chat" not in args:
                cmd.append("chat")

            print(f"🚀 Eseguendo: {' '.join(cmd)}")
            print(f"📝 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

            # Esegui Claude Code
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = process.communicate(input=prompt)

            if process.returncode == 0:
                print("✅ Claude Code completato")
                if stdout.strip():
                    print("\n" + "=" * 50)
                    print(stdout)
                    print("=" * 50)
            else:
                print(f"❌ Errore Claude Code (exit code: {process.returncode})")
                if stderr.strip():
                    print(f"Error: {stderr}")

            return stdout if process.returncode == 0 else None

        except FileNotFoundError:
            print("❌ Claude Code non trovato")
            print("💡 Installa da: https://github.com/anthropics/claude-code")
            return None
        except Exception as e:
            print(f"❌ Errore esecuzione: {e}")
            return None

    async def interactive_session(self):
        """Sessione interattiva voice + Claude Code"""
        print("🎤 Claude Voice Interactive Session")
        print("==================================")
        print("💡 Comandi:")
        print("  • Parla per inviare prompt a Claude")
        print("  • 'exit' o Ctrl+C per uscire")
        print("  • 'context' per vedere contesto corrente")
        print("  • 'templates' per vedere template disponibili")
        print()

        context = self.detect_current_context()
        print(
            f"📁 Contesto rilevato: {context.get('main_language', 'Unknown')} in {os.path.basename(context['pwd'])}"
        )
        print()

        try:
            while True:
                print("🎤 Parla ora (15s timeout)...")

                # Cattura voice input
                voice_text = await self.capture_voice_input(timeout=15)

                if not voice_text:
                    print("⚠️ Nessun input ricevuto, riprova")
                    continue

                # Comandi speciali
                if voice_text.lower() in ["exit", "esci", "quit"]:
                    break
                elif voice_text.lower() == "context":
                    context = self.detect_current_context()
                    print(f"📁 Contesto: {json.dumps(context, indent=2)}")
                    continue
                elif voice_text.lower() == "templates":
                    print("📋 Template disponibili:")
                    for trigger in self.prompt_templates.keys():
                        print(f"  • '{trigger}'")
                    continue

                # Costruisci prompt con contesto
                full_prompt = self.build_context_prompt(voice_text, context)

                # Chiedi conferma
                print("\n📝 Prompt da inviare a Claude:")
                print(f"'{voice_text}'")

                choice = (
                    input("\n💾 [Enter]=Invia [e]=Edita [s]=Salta: ").strip().lower()
                )

                if choice == "e":
                    edited = input("✏️ Modifica prompt:\n> ")
                    if edited.strip():
                        full_prompt = self.build_context_prompt(edited, context)
                        voice_text = edited

                if choice != "s":
                    # Esegui Claude Code
                    await self.run_claude_code(full_prompt)

                    # Aggiorna contesto per prossima iterazione
                    self.session_context.append(voice_text)

                print("\n" + "-" * 50 + "\n")

        except KeyboardInterrupt:
            print("\n👋 Sessione terminata")

    async def quick_prompt(self, voice_prompt=None):
        """Prompt veloce singolo"""
        if not voice_prompt:
            print("🎤 Parla il tuo prompt per Claude...")
            voice_prompt = await self.capture_voice_input()

        if voice_prompt:
            context = self.detect_current_context()
            full_prompt = self.build_context_prompt(voice_prompt, context)
            await self.run_claude_code(full_prompt)
        else:
            print("❌ Nessun input ricevuto")


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Claude Voice - Voice input per Claude Code"
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Modalità interattiva"
    )
    parser.add_argument(
        "--quick", "-q", action="store_true", help="Prompt singolo veloce"
    )
    parser.add_argument("--prompt", "-p", type=str, help="Prompt diretto (senza voice)")
    parser.add_argument(
        "--server", default="ws://localhost:8765", help="URL voice server"
    )

    args = parser.parse_args()

    # Verifica che Claude Code sia disponibile
    try:
        subprocess.run(["claude", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("❌ Claude Code non trovato o non funzionante")
        print("💡 Installa da: https://github.com/anthropics/claude-code")
        print("💡 O verifica che sia nel PATH")
        return

    claude_voice = ClaudeVoice(args.server)

    if not await claude_voice.connect():
        print("❌ Impossibile connettersi al voice server")
        print("💡 Assicurati che sia attivo: ./voice_daemon.sh start")
        return

    try:
        if args.prompt:
            # Prompt diretto senza voice
            context = claude_voice.detect_current_context()
            full_prompt = claude_voice.build_context_prompt(args.prompt, context)
            await claude_voice.run_claude_code(full_prompt)
        elif args.interactive:
            # Modalità interattiva
            await claude_voice.interactive_session()
        elif args.quick:
            # Prompt singolo
            await claude_voice.quick_prompt()
        else:
            # Default: quick mode
            await claude_voice.quick_prompt()

    except KeyboardInterrupt:
        print("\n👋 Uscita")


if __name__ == "__main__":
    asyncio.run(main())
