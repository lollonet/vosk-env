"""Async WebSocket server for voice recognition."""

import asyncio
import json
import logging
from typing import Any, Literal

import websockets
from websockets.exceptions import ConnectionClosed, InvalidMessage

from ..config import settings
from ..engine import VoskEngine
from ..exceptions import VoskEngineError
from ..logging_config import setup_logging
from ..text_correction import correct_text

# Setup logging
logger = logging.getLogger(__name__)
setup_logging()


class VoiceWebSocketServer:
    """Async WebSocket server for voice recognition services."""

    def __init__(self) -> None:
        """Initialize the WebSocket server."""
        self.clients: set[Any] = set()
        self.engines: dict[str, VoskEngine] = {}
        self.current_engine: VoskEngine | None = None
        self.is_permanent_mode = False
        self.current_language = settings.server.default_language

    async def start_server(self, ssl_cert: str | None = None, ssl_key: str | None = None) -> None:
        """Start the WebSocket server with optional SSL support."""
        logger.info(
            f"Starting WebSocket server on {settings.websocket.host}:{settings.websocket.port}"
        )

        # Setup SSL context if certificates provided
        ssl_context = None
        if ssl_cert and ssl_key:
            import ssl
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(ssl_cert, ssl_key)
            protocol = "wss"
            logger.info(f"🔒 SSL enabled - connect via {protocol}://{settings.websocket.host}:{settings.websocket.port}")
        else:
            protocol = "ws"
            logger.info(f"⚠️  No SSL - HTTPS sites may block connection to {protocol}://{settings.websocket.host}:{settings.websocket.port}")

        async with websockets.serve(
            self.handle_client,
            settings.websocket.host,
            settings.websocket.port,
            max_size=settings.websocket.max_size,
            ssl=ssl_context,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10,
        ):
            logger.info(f"✅ WebSocket server started successfully on {protocol}://{settings.websocket.host}:{settings.websocket.port}")
            await asyncio.Future()  # Run forever

    async def handle_client(self, websocket: Any) -> None:
        """Handle new client connections."""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"New client connected: {client_id}")

        self.clients.add(websocket)

        try:
            # Send initial language status
            await self._send_language_status(websocket)
            
            await self._process_client_messages(websocket, client_id)
        except ConnectionClosed:
            logger.info(f"Client {client_id} disconnected normally")
        except InvalidMessage as e:
            logger.warning(f"Invalid message from {client_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error with client {client_id}: {e}")
        finally:
            self.clients.discard(websocket)

    async def _process_client_messages(
        self, websocket: Any, client_id: str
    ) -> None:
        """Process messages from a client."""
        async for message in websocket:
            try:
                data = json.loads(message)
                await self._handle_message(websocket, data, client_id)
            except json.JSONDecodeError:
                await self._send_error(websocket, "Invalid JSON format")
            except Exception as e:
                logger.error(f"Error processing message from {client_id}: {e}")
                await self._send_error(websocket, str(e))

    async def _handle_message(
        self, websocket: Any, data: dict[str, Any], client_id: str
    ) -> None:
        """Handle different message types from clients."""
        action = data.get("action")
        msg_type = data.get("type")  # Some clients might use "type" instead of "action"
        
        logger.info(f"Received message from {client_id}: action={action}, type={msg_type}, data={data}")

        # Check both "action" and "type" fields for compatibility
        command = action or msg_type

        if command == "start_capture" or command == "start_single_capture":
            await self._handle_start_capture(websocket, data, client_id)
        elif command == "stop_capture":
            await self._handle_stop_capture(websocket, client_id)
        elif command == "set_language" or command == "switch_language":
            await self._handle_set_language(websocket, data, client_id)
        elif command == "get_status":
            await self._handle_get_status(websocket, client_id)
        else:
            logger.error(f"Unknown command from {client_id}: {command}")
            await self._send_error(websocket, f"Unknown action: {command}")

    async def _handle_start_capture(
        self, websocket: Any, data: dict[str, Any], client_id: str
    ) -> None:
        """Handle start capture request."""
        context = data.get("context", "browser")
        timeout = data.get("timeout", settings.server.timeout_seconds)

        logger.info(f"Starting capture for {client_id}, context: {context}")

        try:
            engine = await self._get_or_create_engine(self.current_language)
            
            # Test audio device before capture
            import sounddevice as sd
            logger.info(f"Available input devices: {[d['name'] for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0]}")
            
            result = await self._capture_voice_with_timeout(engine, timeout, context)

            await websocket.send(json.dumps({
                "type": "speech_result",
                "text": result,
                "context": context,
                "language": self.current_language
            }))
            logger.info(f"Sent speech result to client: '{result}'")

        except TimeoutError:
            logger.error(f"Voice capture timeout for {client_id}")
            await self._send_error(websocket, "Voice capture timeout")
        except VoskEngineError as e:
            logger.error(f"Voice engine error for {client_id}: {e}")
            await self._send_error(websocket, f"Voice engine error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in start_capture for {client_id}: {e}")
            await self._send_error(websocket, f"Capture failed: {e}")

    async def _handle_stop_capture(
        self, websocket: Any, client_id: str
    ) -> None:
        """Handle stop capture request."""
        logger.info(f"Stopping capture for {client_id}")

        if self.current_engine:
            self.current_engine.stop_listening()

        await websocket.send(json.dumps({
            "type": "status",
            "message": "Capture stopped"
        }))

    async def _handle_set_language(
        self, websocket: Any, data: dict[str, Any], client_id: str
    ) -> None:
        """Handle language change request."""
        try:
            language = data.get("language", "it")

            if language not in ["it", "en"]:
                logger.error(f"Unsupported language requested: {language}")
                await self._send_error(websocket, f"Unsupported language: {language}")
                return

            self.current_language = language
            logger.info(f"Language changed to {language} for {client_id}")

            # Send success response
            response = {
                "type": "language_status",
                "current_language": language,
                "available_languages": ["it", "en"],
                "message": f"Language set to {language}"
            }
            await websocket.send(json.dumps(response))
            logger.info(f"Sent language response: {response}")
        except Exception as e:
            logger.error(f"Error setting language for {client_id}: {e}")
            await self._send_error(websocket, f"Language change failed: {e}")

    async def _handle_get_status(
        self, websocket: Any, client_id: str
    ) -> None:
        """Handle status request."""
        status = {
            "type": "status",
            "language": self.current_language,
            "permanent_mode": self.is_permanent_mode,
            "connected_clients": len(self.clients),
            "available_languages": list(settings.vosk.model_paths.keys())
        }

        await websocket.send(json.dumps(status))

    async def _get_or_create_engine(self, language: str) -> VoskEngine:
        """Get existing engine or create new one for language."""
        if language not in self.engines:
            model_path = settings.vosk.model_paths.get(language)
            if not model_path or not model_path.exists():
                raise VoskEngineError(f"Model not found for language: {language}")

            self.engines[language] = VoskEngine(
                model_path=str(model_path),
                language=language
            )

        self.current_engine = self.engines[language]
        return self.current_engine

    async def _capture_voice_with_timeout(
        self, engine: VoskEngine, timeout: int, context: str
    ) -> str:
        """Capture voice input with timeout."""
        result_queue: asyncio.Queue[str] = asyncio.Queue()

        def on_result(text: str, confidence: float = 0.0) -> None:
            from typing import cast
            logger.info(f"Callback received: text='{text}', confidence={confidence}")
            corrected_text = correct_text(text, cast(Literal["browser", "terminal"], context))
            # Use thread-safe method to put in queue
            try:
                result_queue.put_nowait(corrected_text)
            except asyncio.QueueFull:
                logger.warning("Result queue full, dropping result")

        # Start listening in a separate task
        listen_task = asyncio.create_task(
            self._run_voice_capture(engine, on_result)
        )

        try:
            # Wait for result or timeout
            logger.info(f"Waiting for voice result (timeout: {timeout}s)...")
            result = await asyncio.wait_for(result_queue.get(), timeout=timeout)
            logger.info(f"✅ Got voice result: '{result}'")
            return result
        except TimeoutError:
            logger.warning(f"Voice capture timed out after {timeout}s")
            listen_task.cancel()
            raise
        finally:
            if not listen_task.done():
                listen_task.cancel()

    async def _run_voice_capture(
        self, engine: VoskEngine, callback
    ) -> None:
        """Run voice capture in async context."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, engine.start_listening, callback)

    async def _send_error(self, websocket: Any, message: str) -> None:
        """Send error message to client."""
        error_response = {
            "type": "error",
            "message": message
        }
        logger.error(f"Sending error response: {error_response}")
        await websocket.send(json.dumps(error_response))

    async def _send_language_status(self, websocket: Any) -> None:
        """Send language status to client."""
        status = {
            "type": "language_status",
            "current_language": self.current_language,
            "available_languages": list(settings.vosk.model_paths.keys()),
            "corrections_enabled": self.current_language == "it",
            "listening": self.is_permanent_mode
        }
        await websocket.send(json.dumps(status))
        logger.info(f"Sent language status: {status}")

    async def broadcast_message(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        if not self.clients:
            return

        message_json = json.dumps(message)
        disconnected_clients = set()

        for client in self.clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)

        # Remove disconnected clients
        self.clients -= disconnected_clients


async def start_voice_server(ssl_cert: str | None = None, ssl_key: str | None = None) -> None:
    """Start the voice WebSocket server with optional SSL support."""
    server = VoiceWebSocketServer()
    await server.start_server(ssl_cert=ssl_cert, ssl_key=ssl_key)


if __name__ == "__main__":
    try:
        asyncio.run(start_voice_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
