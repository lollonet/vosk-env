#!/usr/bin/env python3
"""
Async Voice Server - Modern WebSocket server for voice recognition.

This replaces the legacy voice_browser_server.py with a clean, async implementation.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vosk_voice_assistant.servers import start_voice_server


async def main() -> None:
    """Main entry point for the async voice server."""
    try:
        await start_voice_server()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
