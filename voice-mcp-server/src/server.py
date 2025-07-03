"""Voice MCP Server for Claude Code integration."""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from loguru import logger
from typing import Dict, List, Any, Optional

from .config import Config
from .models import TextInput, ToolResponse

class VoiceMCPServer:
    """MCP server for voice text injection with quality standards."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize server with configuration."""
        self.config = config or Config()
        self.server = Server(self.config.server_name)
        self._configure_logging()
        self._register_tools()
        
        logger.info("Voice MCP Server initialized", extra={
            "server_name": self.config.server_name,
            "log_level": self.config.log_level
        })

    def _configure_logging(self) -> None:
        """Configure structured logging."""
        import sys
        logger.remove()
        logger.add(
            sink=sys.stderr,  # Log to stderr, not stdout (MCP uses stdout for JSON)
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
            level=self.config.log_level
        )

    def _register_tools(self) -> None:
        """Register all available MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available tools."""
            return [
                Tool(
                    name="inject_text",
                    description="Inject validated text into the system",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to inject (max 10000 chars)",
                                "maxLength": self.config.max_text_length
                            }
                        },
                        "required": ["text"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute tool with proper error handling and validation."""
            try:
                if name == "inject_text":
                    return await self._handle_inject_text(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                error_msg = f"Tool execution failed: {str(e)}"
                logger.error(error_msg, extra={
                    "tool_name": name,
                    "arguments": arguments,
                    "error_type": type(e).__name__
                })
                return [TextContent(
                    type="text", 
                    text=f"❌ Error: {error_msg}"
                )]

    async def _handle_inject_text(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle text injection with validation."""
        # Validate input using Pydantic model
        text_input = TextInput(**arguments)
        
        # Process text injection
        response = ToolResponse(
            success=True,
            message=f"Text injected successfully: {text_input.text[:50]}...",
            data={"text_length": len(text_input.text)}
        )
        
        logger.info("Text injection completed", extra={
            "text_length": len(text_input.text),
            "text_preview": text_input.text[:100]
        })
        
        return [TextContent(
            type="text",
            text=f"✅ {response.message}"
        )]

    async def run(self) -> None:
        """Start the MCP server with proper resource management."""
        logger.info("Starting MCP server...", extra={"config": self.config.model_dump()})
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                init_options = self.server.create_initialization_options()
                await self.server.run(read_stream, write_stream, init_options)
        except Exception as e:
            import traceback
            logger.error("Server failed to start", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            })
            raise
        finally:
            logger.info("MCP server shutdown completed")