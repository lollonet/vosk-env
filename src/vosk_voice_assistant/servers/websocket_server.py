"""Async WebSocket server for voice recognition."""

import asyncio
import json
import logging
from typing import Any, Literal

import websockets

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

    async def start_server(self) -> None:
        """Start the WebSocket server."""
        logger.info(
            f"Starting WebSocket server on {settings.websocket.host}:{settings.websocket.port}"
        )

        async with websockets.serve(
            self.handle_client,
            settings.websocket.host,
            settings.websocket.port,
            max_size=settings.websocket.max_size,
        ):
            logger.info("WebSocket server started successfully")
            await asyncio.Future()  # Run forever

    async def handle_client(self, websocket: Any, path: str) -> None:
        """Handle new client connections."""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"New client connected: {client_id}")

        self.clients.add(websocket)

        try:
            await self._process_client_messages(websocket, client_id)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
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

        if action == "start_capture":
            await self._handle_start_capture(websocket, data, client_id)
        elif action == "stop_capture":
            await self._handle_stop_capture(websocket, client_id)
        elif action == "set_language":
            await self._handle_set_language(websocket, data, client_id)
        elif action == "get_status":
            await self._handle_get_status(websocket, client_id)
        else:
            await self._send_error(websocket, f"Unknown action: {action}")

    async def _handle_start_capture(
        self, websocket: Any, data: dict[str, Any], client_id: str
    ) -> None:
        """Handle start capture request."""
        context = data.get("context", "browser")
        timeout = data.get("timeout", settings.server.timeout_seconds)

        logger.info(f"Starting capture for {client_id}, context: {context}")

        try:
            engine = await self._get_or_create_engine(self.current_language)
            result = await self._capture_voice_with_timeout(engine, timeout, context)

            await websocket.send(json.dumps({
                "type": "result",
                "text": result,
                "context": context,
                "language": self.current_language
            }))

        except TimeoutError:
            await self._send_error(websocket, "Voice capture timeout")
        except VoskEngineError as e:
            await self._send_error(websocket, f"Voice engine error: {e}")

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
        language = data.get("language", "it")

        if language not in ["it", "en"]:
            await self._send_error(websocket, f"Unsupported language: {language}")
            return

        self.current_language = language
        logger.info(f"Language changed to {language} for {client_id}")

        await websocket.send(json.dumps({
            "type": "status",
            "message": f"Language set to {language}"
        }))

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

        def on_result(text: str) -> None:
            from typing import cast
            corrected_text = correct_text(text, cast(Literal["browser", "terminal"], context))
            asyncio.create_task(result_queue.put(corrected_text))

        # Start listening in a separate task
        listen_task = asyncio.create_task(
            self._run_voice_capture(engine, on_result)
        )

        try:
            # Wait for result or timeout
            result = await asyncio.wait_for(result_queue.get(), timeout=timeout)
            return result
        except TimeoutError:
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
        await websocket.send(json.dumps(error_response))

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


async def start_voice_server() -> None:
    """Start the voice WebSocket server."""
    server = VoiceWebSocketServer()
    await server.start_server()


if __name__ == "__main__":
    try:
        asyncio.run(start_voice_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
