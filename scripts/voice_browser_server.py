#!/usr/bin/env python3
import asyncio
import json
import queue
import re
import threading
from pathlib import Path

import websockets
from vosk_engine import VoskEngine

clients = set()
message_queue = queue.Queue()
current_engine = None
engines = {}
is_permanent_mode = False
current_language = "it"

# Dizionario correzioni termini IT (per browser)
IT_TECH_TERMS = {
    "ghit ab": "github",
    "git ab": "github",
    "git hub": "github",
    "docher": "docker",
    "kubernet": "kubernetes",
    "react": "react",
    "nod jes": "nodejs",
    "javascript": "javascript",
    "python": "python",
    "api": "API",
    "ei pi ai": "API",
    "rest": "REST",
    # ... (resto del dizionario IT come prima)
}

# Dizionario comandi Linux (per terminale)
LINUX_COMMANDS = {
    "elle es": "ls",
    "liste": "ls",
    "lista": "ls",
    "liste la": "ls -la",
    "ci di": "cd",
    "vai in": "cd",
    "pi uadiblu": "pwd",
    "dove sono": "pwd",
    "tocca": "touch",
    "crea file": "touch",
    "mkdir": "mkdir",
    "copia": "cp",
    "sposta": "mv",
    "rimuovi": "rm",
    "cat": "cat",
    "mostra": "cat",
    "grep": "grep",
    "pi es": "ps",
    "processi": "ps aux",
    "top": "top",
    "df": "df -h",
    "spazio disco": "df -h",
    "free": "free -h",
    "memoria": "free -h",
    "ping": "ping",
    "wget": "wget",
    "curl": "curl",
    "git": "git",
    "git status": "git status",
    "stato git": "git status",
    "git add": "git add",
    "git commit": "git commit",
    "git push": "git push",
    "pus": "git push",
    "docker": "docker",
    "container": "docker ps",
    "sudo": "sudo",
    "installa": "sudo apt install",
    # ... (resto dei comandi Linux)
}


def correct_text(text, context="browser"):
    """Corregge testo in base al contesto"""
    if not text.strip():
        return text

    original_text = text
    corrected_text = text.lower()

    if context == "browser" and current_language == "it":
        # Correzioni termini IT per browser
        for wrong, correct in IT_TECH_TERMS.items():
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            corrected_text = pattern.sub(correct, corrected_text)

    elif context == "terminal":
        # Correzioni comandi Linux per terminale
        for voice_cmd, real_cmd in LINUX_COMMANDS.items():
            if corrected_text == voice_cmd or corrected_text.startswith(
                voice_cmd + " "
            ):
                remainder = corrected_text[len(voice_cmd) :].strip()
                corrected_text = real_cmd + (" " + remainder if remainder else "")
                break

    if corrected_text != original_text.lower():
        print(f"🔧 Correzione {context}: '{original_text}' → '{corrected_text}'")

    return corrected_text


def load_engines():
    """Carica modelli"""
    global engines

    models_dir = Path.home() / "vosk-env" / "models"

    try:
        print("🔄 Caricamento modello italiano...")
        engines["it"] = VoskEngine(str(models_dir / "italian"))
        print("✅ Modello italiano caricato")
    except Exception as e:
        print(f"❌ Errore modello italiano: {e}")

    try:
        print("🔄 Caricamento modello inglese...")
        engines["en"] = VoskEngine(str(models_dir / "english"))
        print("✅ Modello inglese caricato")
    except Exception as e:
        print(f"❌ Errore modello inglese: {e}")


def switch_language(new_lang):
    """Cambia lingua"""
    global current_engine, current_language, is_permanent_mode

    if new_lang not in engines:
        return False

    if current_engine and is_permanent_mode:
        current_engine.stop_listening()

    current_language = new_lang
    current_engine = engines[new_lang]

    if is_permanent_mode:

        def start_listening_closure(engine):
            engine.start_listening(callback=voice_callback)

        threading.Thread(
            target=lambda: start_listening_closure(current_engine), daemon=True
        ).start()

    message_queue.put(
        {
            "type": "language_switched",
            "language": new_lang,
            "corrections_enabled": new_lang == "it",
        }
    )

    return True


def voice_callback(text, confidence):
    """Callback standard per browser"""
    if text.strip():
        corrected_text = correct_text(text, "browser")
        original = text if corrected_text != text else None

        message_queue.put(
            {
                "type": "speech_result",
                "text": corrected_text,
                "original_text": original,
                "confidence": confidence,
                "language": current_language,
            }
        )


def terminal_voice_callback(text, confidence):
    """Callback specializzato per terminale"""
    if text.strip():
        corrected_text = correct_text(text, "terminal")
        original = text if corrected_text != text else None

        message_queue.put(
            {
                "type": "speech_result",
                "text": corrected_text,
                "original_text": original,
                "confidence": confidence,
                "context": "terminal",
            }
        )


async def handle_websocket(websocket):
    global current_engine, is_permanent_mode, current_language

    clients.add(websocket)
    print(f"🔗 Client connesso ({len(clients)} totali)")

    # Invia stato iniziale
    await websocket.send(
        json.dumps(
            {
                "type": "language_status",
                "current_language": current_language,
                "available_languages": list(engines.keys()),
                "corrections_enabled": current_language == "it",
            }
        )
    )

    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "start_permanent_listening":
                # Browser: listening permanente
                is_permanent_mode = True
                current_engine = engines.get(current_language)
                engine_to_use = current_engine
                if engine_to_use:
                    import functools

                    bound_start = functools.partial(
                        engine_to_use.start_listening, callback=voice_callback
                    )
                    threading.Thread(target=bound_start, daemon=True).start()
                await websocket.send(json.dumps({"type": "listening_started"}))
                print(f"🎤 Browser voice ATTIVO ({current_language.upper()})")

            elif msg_type == "stop_permanent_listening":
                # Browser: stop listening
                is_permanent_mode = False
                if current_engine:
                    current_engine.stop_listening()
                await websocket.send(json.dumps({"type": "listening_stopped"}))
                print("🛑 Browser voice DISATTIVATO")

            elif msg_type == "start_single_capture":
                # Terminale: cattura singola (10 secondi max)
                current_engine = engines.get(current_language)
                engine_for_single = current_engine
                if engine_for_single:

                    def single_callback(text, confidence, engine=engine_for_single):
                        corrected_text = correct_text(text, "terminal")
                        original = text if corrected_text != text else None

                        message_queue.put(
                            {
                                "type": "speech_result",
                                "text": corrected_text,
                                "original_text": original,
                                "confidence": confidence,
                                "context": "terminal",
                                "single_capture": True,
                            }
                        )
                        # Use the engine passed as default parameter
                        if engine:
                            engine.stop_listening()

                    # Use functools.partial to bind the engine and callback
                    import functools

                    bound_start_single = functools.partial(
                        engine_for_single.start_listening,
                        callback=single_callback,
                        duration=10,
                    )
                    threading.Thread(target=bound_start_single, daemon=True).start()

                await websocket.send(json.dumps({"type": "single_capture_started"}))
                print("🎤 Terminal voice capture ATTIVO (10s)")

            elif msg_type == "switch_language":
                # Switch lingua
                requested_lang = data.get("language")
                if switch_language(requested_lang):
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "language_switched",
                                "language": current_language,
                                "corrections_enabled": current_language == "it",
                            }
                        )
                    )
                    print(f"🔄 Lingua cambiata: {current_language.upper()}")
                else:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "error",
                                "message": f"Lingua {requested_lang} non disponibile",
                            }
                        )
                    )

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"❌ Errore client: {e}")
    finally:
        clients.discard(websocket)
        print(f"🔌 Client disconnesso ({len(clients)} rimasti)")


async def message_sender():
    """Invia messaggi ai client"""
    while True:
        try:
            msg = message_queue.get_nowait()
            if clients:
                disconnected = set()
                for client in clients:
                    try:
                        await client.send(json.dumps(msg))
                    except (websockets.exceptions.ConnectionClosed, ConnectionError):
                        disconnected.add(client)
                clients.difference_update(disconnected)
        except queue.Empty:
            await asyncio.sleep(0.1)


async def main():
    global current_language, current_engine

    print("🚀 Voice Input Server Multi-Context (Browser + Terminal)")
    print("========================================================")

    # Carica modelli
    load_engines()

    if not engines:
        print("❌ Nessun modello caricato!")
        return

    # Imposta lingua default
    current_language = "it" if "it" in engines else list(engines.keys())[0]
    current_engine = engines[current_language]

    print(f"✅ Modelli caricati: {list(engines.keys())}")
    print(f"🌍 Lingua default: {current_language.upper()}")
    print(
        f"🔧 Correzioni IT: {'ABILITATE' if current_language == 'it' else 'DISABILITATE'}"
    )
    print("🖥️  Supporto Browser: Permanente + switch lingua")
    print("💻 Supporto Terminal: Single capture + comandi Linux")

    # Avvia message sender
    asyncio.create_task(message_sender())

    # Avvia server
    async with websockets.serve(handle_websocket, "localhost", 8765):
        print("✅ Server attivo su porta 8765")
        print("🎤 Browser: Ctrl+/ (toggle), Ctrl+? (lingua)")
        print("💻 Terminal: voice-terminal start")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
