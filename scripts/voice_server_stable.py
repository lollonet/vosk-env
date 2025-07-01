#!/usr/bin/env python3
"""
Stable Voice Server - Rewritten for reliability and proper resource management
"""

import asyncio
import json
import logging
import signal
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Dict, Optional, Set, Callable
import threading
import time

import websockets
from websockets.exceptions import ConnectionClosed, InvalidMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('voice_server')

# Suppress VOSK warnings
logging.getLogger('vosk').setLevel(logging.ERROR)

@dataclass
class VoiceResult:
    text: str
    confidence: float
    language: str
    original_text: Optional[str] = None
    context: str = "browser"

class VoiceEngine:
    """Thread-safe wrapper for Vosk engine"""
    
    def __init__(self, model_path: str, language: str):
        self.model_path = model_path
        self.language = language
        self._engine = None
        self._lock = Lock()
        self._listening = False
        self._initialize()
    
    def _initialize(self):
        """Initialize Vosk engine"""
        try:
            from vosk_engine_native import VoskEngineNative
            self._engine = VoskEngineNative(self.model_path)
            logger.info(f"✅ {self.language.upper()} model loaded from {self.model_path}")
        except Exception as e:
            logger.error(f"❌ Failed to load {self.language} model: {e}")
            raise
    
    def start_listening(self, callback: Callable[[str, float], None], duration: Optional[int] = None):
        """Start listening with thread safety"""
        with self._lock:
            if self._listening:
                logger.warning(f"Engine {self.language} already listening")
                return
            
            self._listening = True
            
        try:
            if duration:
                self._engine.start_listening(callback=callback, duration=duration)
            else:
                self._engine.start_listening(callback=callback)
        except Exception as e:
            logger.error(f"Error starting listening for {self.language}: {e}")
            with self._lock:
                self._listening = False
            raise
        finally:
            # Always reset listening flag when underlying engine returns
            with self._lock:
                self._listening = False
    
    def stop_listening(self):
        """Stop listening with thread safety"""
        with self._lock:
            if not self._listening:
                return
            
            self._listening = False
            
        try:
            if self._engine:
                self._engine.stop_listening()
        except Exception as e:
            logger.error(f"Error stopping listening for {self.language}: {e}")
    
    @property
    def is_listening(self) -> bool:
        with self._lock:
            return self._listening

class TextCorrector:
    """Text correction for different contexts"""
    
    IT_TECH_TERMS = {
        "ghit ab": "github", "git ab": "github", "git hub": "github",
        "docher": "docker", "kubernet": "kubernetes", "react": "react",
        "nod jes": "nodejs", "javascript": "javascript", "python": "python",
        "api": "API", "ei pi ai": "API", "rest": "REST",
    }
    
    LINUX_COMMANDS = {
        "elle es": "ls", "liste": "ls", "lista": "ls",
        "ci di": "cd", "vai in": "cd", "pi uadiblu": "pwd",
        "dove sono": "pwd", "tocca": "touch", "crea file": "touch",
        "mkdir": "mkdir", "copia": "cp", "sposta": "mv",
        "rimuovi": "rm", "cat": "cat", "mostra": "cat",
        "git status": "git status", "stato git": "git status",
    }
    
    @classmethod
    def correct_text(cls, text: str, context: str = "browser") -> tuple[str, bool]:
        """Correct text based on context"""
        if not text.strip():
            return text, False
        
        original = text
        corrected = text.lower()
        
        if context == "browser":
            for wrong, correct in cls.IT_TECH_TERMS.items():
                if wrong in corrected:
                    corrected = corrected.replace(wrong, correct)
        elif context == "terminal":
            for voice_cmd, real_cmd in cls.LINUX_COMMANDS.items():
                if corrected == voice_cmd or corrected.startswith(voice_cmd + " "):
                    remainder = corrected[len(voice_cmd):].strip()
                    corrected = real_cmd + (" " + remainder if remainder else "")
                    break
        
        was_corrected = corrected != original.lower()
        return corrected, was_corrected

class VoiceServer:
    """Main voice server with proper resource management"""
    
    def __init__(self, host: str = "localhost", port: int = 8765, use_large_models: bool = True, 
                 ssl_cert: Optional[str] = None, ssl_key: Optional[str] = None):
        self.host = host
        self.port = port
        self.use_large_models = use_large_models
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.engines: Dict[str, VoiceEngine] = {}
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.current_language = "it"
        self.permanent_listening = False
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self._shutdown_event = asyncio.Event()
        self._listening_thread: Optional[threading.Thread] = None
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Load engines
        self._load_engines()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(self.shutdown())
    
    def _load_engines(self):
        """Load available voice engines"""
        models_dir = Path.home() / "vosk-env" / "models"
        
        if self.use_large_models:
            # Use LARGE models for better recognition quality
            models = {
                "en": "models/english", 
                "it": "models/italian"  # High-quality large models (2.7GB/2.0GB)
            }
            logger.info("🔥 Using LARGE models for maximum recognition quality")
        else:
            # Use SMALL models for faster loading and lower memory usage
            models = {
                "en": "models-small-backup/vosk-model-small-en-us-0.15", 
                "it": "models-small-backup/vosk-model-small-it-0.22"  # Small models (68MB/88MB)
            }
            logger.info("⚡ Using SMALL models for fast performance")
        
        for lang_code, model_subpath in models.items():
            model_path = models_dir.parent / model_subpath
            if model_path.exists():
                try:
                    self.engines[lang_code] = VoiceEngine(str(model_path), lang_code)
                except Exception as e:
                    logger.error(f"Failed to load {lang_code} engine: {e}")
        
        if not self.engines:
            raise RuntimeError("No voice engines could be loaded")
        
        # Set default language
        self.current_language = "it" if "it" in self.engines else list(self.engines.keys())[0]
        logger.info(f"Available languages: {list(self.engines.keys())}")
        logger.info(f"Default language: {self.current_language}")
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol):
        """Handle individual client connections"""
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"🔗 Client connected: {client_addr}")
        
        self.clients.add(websocket)
        
        try:
            # Send initial status
            await self._send_language_status(websocket)
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from {client_addr}: {message}")
                    await self._send_error(websocket, "Invalid JSON message")
                except Exception as e:
                    logger.error(f"Error handling message from {client_addr}: {e}")
                    await self._send_error(websocket, str(e))
                    
        except ConnectionClosed:
            logger.info(f"Client {client_addr} disconnected normally")
        except InvalidMessage as e:
            logger.warning(f"Invalid message from {client_addr}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error with client {client_addr}: {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"🔌 Client removed: {client_addr} ({len(self.clients)} remaining)")
    
    async def _handle_message(self, websocket: websockets.WebSocketServerProtocol, data: dict):
        """Handle client messages"""
        msg_type = data.get("type")
        
        if msg_type == "start_permanent_listening":
            await self._start_permanent_listening(websocket)
        elif msg_type == "stop_permanent_listening":
            await self._stop_permanent_listening(websocket)
        elif msg_type == "start_single_capture":
            await self._start_single_capture(websocket)
        elif msg_type == "switch_language":
            await self._switch_language(websocket, data.get("language"))
        elif msg_type == "get_language_status":
            await self._send_language_status(websocket)
        else:
            await self._send_error(websocket, f"Unknown message type: {msg_type}")
    
    async def _start_permanent_listening(self, websocket: websockets.WebSocketServerProtocol):
        """Start permanent listening mode"""
        if self.current_language not in self.engines:
            await self._send_error(websocket, f"Language {self.current_language} not available")
            return
        
        engine = self.engines[self.current_language]
        
        if engine.is_listening:
            await self._send_error(websocket, "Already listening")
            return
        
        def voice_callback(text: str, confidence: float):
            if text.strip():
                corrected_text, was_corrected = TextCorrector.correct_text(text, "browser")
                result = VoiceResult(
                    text=corrected_text,
                    confidence=confidence,
                    language=self.current_language,
                    original_text=text if was_corrected else None,
                    context="browser"
                )
                # Thread-safe way to schedule coroutine in the main event loop
                try:
                    if self._main_loop:
                        asyncio.run_coroutine_threadsafe(self._broadcast_result(result), self._main_loop)
                except Exception as e:
                    logger.error(f"Error broadcasting result: {e}")
        
        try:
            # Start listening in a separate thread to avoid blocking
            def start_listening():
                engine.start_listening(voice_callback)
            
            self._listening_thread = threading.Thread(target=start_listening, daemon=True)
            self._listening_thread.start()
            self.permanent_listening = True
            
            await websocket.send(json.dumps({"type": "listening_started"}))
            logger.info(f"🎤 Permanent listening started ({self.current_language.upper()})")
            
        except Exception as e:
            logger.error(f"Failed to start permanent listening: {e}")
            await self._send_error(websocket, f"Failed to start listening: {e}")
    
    async def _stop_permanent_listening(self, websocket: websockets.WebSocketServerProtocol):
        """Stop permanent listening mode"""
        if not self.permanent_listening:
            await websocket.send(json.dumps({"type": "listening_stopped"}))
            return
        
        try:
            if self.current_language in self.engines:
                self.engines[self.current_language].stop_listening()
            
            # Wait for listening thread to finish
            if self._listening_thread and self._listening_thread.is_alive():
                logger.info("⏳ Waiting for listening thread to finish...")
                self._listening_thread.join(timeout=3.0)
            
            self.permanent_listening = False
            self._listening_thread = None
            await websocket.send(json.dumps({"type": "listening_stopped"}))
            logger.info("🛑 Permanent listening stopped")
            
        except Exception as e:
            logger.error(f"Error stopping permanent listening: {e}")
            await self._send_error(websocket, f"Failed to stop listening: {e}")
    
    async def _start_single_capture(self, websocket: websockets.WebSocketServerProtocol):
        """Start single capture mode"""
        if self.current_language not in self.engines:
            await self._send_error(websocket, f"Language {self.current_language} not available")
            return
        
        engine = self.engines[self.current_language]
        capture_completed = asyncio.Event()
        result_data = {}
        
        def single_callback(text: str, confidence: float):
            if text.strip():
                corrected_text, was_corrected = TextCorrector.correct_text(text, "terminal")
                result_data.update({
                    "text": corrected_text,
                    "confidence": confidence,
                    "original_text": text if was_corrected else None,
                    "context": "terminal"
                })
            capture_completed.set()
        
        try:
            def start_single_capture():
                engine.start_listening(single_callback, duration=10)
            
            threading.Thread(target=start_single_capture, daemon=True).start()
            
            await websocket.send(json.dumps({"type": "single_capture_started"}))
            logger.info("🎤 Single capture started (10s timeout)")
            
            # Wait for completion or timeout
            try:
                await asyncio.wait_for(capture_completed.wait(), timeout=12.0)
                
                if result_data:
                    result = VoiceResult(
                        text=result_data["text"],
                        confidence=result_data["confidence"],
                        language=self.current_language,
                        original_text=result_data.get("original_text"),
                        context="terminal"
                    )
                    await self._send_result(websocket, result)
                else:
                    await self._send_error(websocket, "No voice input detected")
                    
            except asyncio.TimeoutError:
                await self._send_error(websocket, "Single capture timeout")
                logger.warning("Single capture timed out")
            
        except Exception as e:
            logger.error(f"Error in single capture: {e}")
            await self._send_error(websocket, f"Single capture failed: {e}")
    
    async def _switch_language(self, websocket: websockets.WebSocketServerProtocol, language: str):
        """Switch language"""
        if not language or language not in self.engines:
            await self._send_error(websocket, f"Language {language} not available")
            return
        
        # Stop current listening if active
        if self.permanent_listening and self.current_language in self.engines:
            self.engines[self.current_language].stop_listening()
            
            # Wait for old thread to finish before starting new one
            if self._listening_thread and self._listening_thread.is_alive():
                logger.info("⏳ Waiting for old listening thread to finish...")
                self._listening_thread.join(timeout=3.0)
                if self._listening_thread.is_alive():
                    logger.warning("⚠️ Old thread did not finish in time")
        
        old_language = self.current_language
        self.current_language = language
        
        # Restart listening if it was active
        if self.permanent_listening:
            await self._start_permanent_listening(websocket)
        
        await self._send_language_status(websocket)
        logger.info(f"🔄 Language switched: {old_language} → {language}")
    
    async def _send_language_status(self, websocket: websockets.WebSocketServerProtocol):
        """Send language status to client"""
        status = {
            "type": "language_status",
            "current_language": self.current_language,
            "available_languages": list(self.engines.keys()),
            "corrections_enabled": self.current_language == "it",
            "listening": self.permanent_listening
        }
        await websocket.send(json.dumps(status))
    
    async def _send_result(self, websocket: websockets.WebSocketServerProtocol, result: VoiceResult):
        """Send voice result to client"""
        message = {
            "type": "speech_result",
            "text": result.text,
            "confidence": result.confidence,
            "language": result.language,
            "context": result.context
        }
        if result.original_text:
            message["original_text"] = result.original_text
        
        await websocket.send(json.dumps(message))
    
    async def _send_error(self, websocket: websockets.WebSocketServerProtocol, error: str):
        """Send error message to client"""
        await websocket.send(json.dumps({"type": "error", "message": error}))
    
    async def _broadcast_result(self, result: VoiceResult):
        """Broadcast result to all connected clients"""
        if not self.clients:
            return
        
        message = {
            "type": "speech_result",
            "text": result.text,
            "confidence": result.confidence,
            "language": result.language,
            "context": result.context
        }
        if result.original_text:
            message["original_text"] = result.original_text
        
        message_json = json.dumps(message)
        disconnected = set()
        
        for client in self.clients.copy():
            try:
                await client.send(message_json)
            except ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(client)
        
        self.clients.difference_update(disconnected)
    
    async def shutdown(self):
        """Gracefully shutdown the server"""
        logger.info("🛑 Shutting down voice server...")
        self.running = False
        
        # Stop all engines
        for engine in self.engines.values():
            try:
                engine.stop_listening()
            except Exception as e:
                logger.error(f"Error stopping engine: {e}")
        
        # Wait for listening thread to finish
        if self._listening_thread and self._listening_thread.is_alive():
            logger.info("⏳ Waiting for listening thread to finish...")
            self._listening_thread.join(timeout=3.0)
        
        # Close all client connections
        if self.clients:
            logger.info(f"Closing {len(self.clients)} client connections...")
            for client in self.clients.copy():
                try:
                    await client.close()
                except Exception:
                    pass
        
        self._shutdown_event.set()
        logger.info("✅ Voice server shutdown complete")
    
    async def run(self):
        """Run the voice server"""
        logger.info("🚀 Starting Voice Server")
        logger.info("=" * 50)
        logger.info(f"Host: {self.host}:{self.port}")
        logger.info(f"Model Type: {'LARGE (High Quality)' if self.use_large_models else 'SMALL (Fast)'}")
        logger.info(f"Languages: {list(self.engines.keys())}")
        logger.info(f"Default: {self.current_language.upper()}")
        logger.info("=" * 50)
        
        self.running = True
        
        # Store reference to main event loop for thread-safe callbacks
        self._main_loop = asyncio.get_event_loop()
        
        try:
            # Setup SSL context if certificates provided
            ssl_context = None
            if self.ssl_cert and self.ssl_key:
                import ssl
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(self.ssl_cert, self.ssl_key)
                protocol = "wss" if ssl_context else "ws"
                logger.info(f"🔒 SSL enabled - connect via {protocol}://{self.host}:{self.port}")
            else:
                protocol = "ws"
                logger.info(f"⚠️  No SSL - HTTPS sites may block connection to {protocol}://{self.host}:{self.port}")
            
            async with websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ):
                logger.info(f"✅ Voice server listening on {protocol}://{self.host}:{self.port}")
                logger.info("🎤 Ready for connections...")
                
                # Wait for shutdown signal
                await self._shutdown_event.wait()
                
        except Exception as e:
            logger.error(f"❌ Server error: {e}")
            raise

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Voice Server with Native Audio Capture")
    parser.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="Server port (default: 8765)")
    parser.add_argument("--small-models", action="store_true", 
                       help="Use small models for faster loading (default: use large models)")
    parser.add_argument("--ssl-cert", help="SSL certificate file for HTTPS support")
    parser.add_argument("--ssl-key", help="SSL private key file for HTTPS support")
    parser.add_argument("--generate-ssl", action="store_true", 
                       help="Generate self-signed SSL certificates automatically")
    
    args = parser.parse_args()
    
    # Handle SSL certificate generation
    ssl_cert, ssl_key = None, None
    if args.generate_ssl:
        import subprocess
        import tempfile
        import os
        
        cert_dir = tempfile.mkdtemp()
        ssl_cert = os.path.join(cert_dir, "voice_server_cert.pem")
        ssl_key = os.path.join(cert_dir, "voice_server_key.pem")
        
        print("🔒 Generating self-signed SSL certificate...")
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", 
            "-keyout", ssl_key, "-out", ssl_cert, "-days", "365", "-nodes",
            "-subj", "/C=IT/ST=Italy/L=Local/O=VoiceServer/CN=localhost"
        ], check=True, capture_output=True)
        print(f"✅ SSL certificate generated: {ssl_cert}")
        
    elif args.ssl_cert and args.ssl_key:
        ssl_cert, ssl_key = args.ssl_cert, args.ssl_key
    
    try:
        server = VoiceServer(
            host=args.host, 
            port=args.port, 
            use_large_models=not args.small_models,
            ssl_cert=ssl_cert,
            ssl_key=ssl_key
        )
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("👋 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()