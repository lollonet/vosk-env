#!/usr/bin/env python3
"""
MCP Voice Server - Voice input integration per Claude Code
Espone tool voice_listen() che si connette al daemon Vosk esistente
"""

import asyncio
import json
import sys
import logging
from typing import Any, Dict
import websockets

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("❌ MCP library non trovata. Installa con: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-mcp")

class VoiceMCPServer:
    def __init__(self, voice_server_url='ws://localhost:8765'):
        self.voice_server_url = voice_server_url
        self.server = Server("voice-input")
        
        # Correzioni terminologia sviluppo
        self.dev_corrections = {
            'paiton': 'python', 'giava script': 'javascript',
            'react': 'React', 'nod jes': 'nodejs', 'vue jes': 'Vue.js',
            'django': 'Django', 'flask': 'Flask', 'express': 'Express',
            'mai sequel': 'MySQL', 'postgres': 'PostgreSQL', 'mongo db': 'MongoDB',
            'docher': 'Docker', 'kubernetes': 'Kubernetes', 'git': 'Git',
            'ei pi ai': 'API', 'rest': 'REST', 'graphql': 'GraphQL',
            'debug': 'debug', 'refactor': 'refactor', 'ottimizza': 'optimize',
            'spiega': 'explain', 'crea': 'create', 'implementa': 'implement',
            'claude aiuto': 'help me', 'claude crea': 'create', 'claude spiega': 'explain',
            'claude debug': 'debug', 'claude ottimizza': 'optimize',
        }
        
        # Registra tools
        self.setup_tools()
    
    def setup_tools(self):
        """Registra MCP tools"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="voice_listen",
                    description="Captures voice input and converts to text using Vosk speech recognition",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "timeout": {
                                "type": "number",
                                "description": "Timeout in seconds for voice capture (default: 15)",
                                "default": 15
                            },
                            "language": {
                                "type": "string", 
                                "description": "Language for speech recognition (it/en)",
                                "default": "it"
                            }
                        }
                    }
                ),
                Tool(
                    name="voice_status",
                    description="Check voice daemon status and available languages",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
            logger.info(f"Tool chiamato: {name} con args: {arguments}")
            
            if name == "voice_listen":
                return await self.handle_voice_listen(arguments)
            elif name == "voice_status":
                return await self.handle_voice_status(arguments)
            else:
                return [TextContent(type="text", text=f"Tool sconosciuto: {name}")]
    
    async def handle_voice_listen(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Gestisce voice_listen tool"""
        timeout = arguments.get("timeout", 15)
        language = arguments.get("language", "it")
        
        try:
            # Connetti al voice daemon
            async with websockets.connect(self.voice_server_url) as websocket:
                logger.info(f"Connesso al voice daemon: {self.voice_server_url}")
                
                # Imposta lingua se necessario
                if language:
                    await websocket.send(json.dumps({
                        'type': 'set_language',
                        'language': language
                    }))
                
                # Richiedi voice capture
                await websocket.send(json.dumps({
                    'type': 'start_single_capture'
                }))
                
                logger.info(f"Voice capture avviato (timeout: {timeout}s)")
                
                # Attendi risposta con timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                    data = json.loads(response)
                    
                    if data.get('type') == 'speech_result':
                        raw_text = data.get('text', '').strip()
                        if raw_text:
                            # Applica correzioni
                            corrected_text = self.correct_dev_text(raw_text)
                            
                            result = f"🎤 Voice Input Captured:\n\n"
                            result += f"Raw: {raw_text}\n"
                            if corrected_text != raw_text:
                                result += f"Corrected: {corrected_text}\n\n"
                            else:
                                result += f"\n"
                            result += f"Text: {corrected_text}"
                            
                            logger.info(f"Voice capture success: {corrected_text}")
                            return [TextContent(type="text", text=result)]
                        else:
                            return [TextContent(type="text", text="❌ No voice input detected")]
                    else:
                        return [TextContent(type="text", text=f"❌ Unexpected response: {data}")]
                        
                except asyncio.TimeoutError:
                    logger.warning(f"Voice capture timeout dopo {timeout}s")
                    return [TextContent(type="text", text=f"⏰ Voice capture timeout dopo {timeout} secondi")]
                    
        except Exception as e:
            error_msg = f"❌ Errore voice capture: {str(e)}"
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]
    
    async def handle_voice_status(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Gestisce voice_status tool"""
        try:
            async with websockets.connect(self.voice_server_url) as websocket:
                # Richiedi status
                await websocket.send(json.dumps({
                    'type': 'get_language_status'
                }))
                
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)
                
                if data.get('type') == 'language_status':
                    current_lang = data.get('current_language', 'unknown')
                    available_langs = data.get('available_languages', [])
                    corrections_enabled = data.get('corrections_enabled', False)
                    
                    result = f"🎤 Voice Daemon Status:\n\n"
                    result += f"Status: ✅ ACTIVE\n"
                    result += f"URL: {self.voice_server_url}\n"
                    result += f"Current Language: {current_lang}\n"
                    result += f"Available Languages: {', '.join(available_langs)}\n"
                    result += f"Corrections Enabled: {'✅' if corrections_enabled else '❌'}\n"
                    
                    return [TextContent(type="text", text=result)]
                else:
                    return [TextContent(type="text", text=f"❌ Unexpected status response: {data}")]
                    
        except Exception as e:
            error_msg = f"❌ Voice daemon non disponibile: {str(e)}\n"
            error_msg += f"💡 Assicurati che sia attivo: ./voice_daemon.sh start"
            return [TextContent(type="text", text=error_msg)]
    
    def correct_dev_text(self, text: str) -> str:
        """Correggi terminologia per sviluppo"""
        if not text.strip():
            return text
        
        corrected = text.lower()
        for wrong, correct in self.dev_corrections.items():
            corrected = corrected.replace(wrong, correct)
        
        # Capitalizza prima lettera per Claude
        corrected = corrected.strip()
        if corrected:
            corrected = corrected[0].upper() + corrected[1:] if len(corrected) > 1 else corrected.upper()
        
        return corrected

async def main():
    """Main MCP server"""
    logger.info("🎤 Starting Voice MCP Server...")
    
    # Crea server
    voice_server = VoiceMCPServer()
    
    # Avvia server MCP
    async with stdio_server() as (read_stream, write_stream):
        logger.info("✅ Voice MCP Server ready")
        await voice_server.server.run(
            read_stream,
            write_stream,
            voice_server.server.create_initialization_options()
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Voice MCP Server stopped")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)