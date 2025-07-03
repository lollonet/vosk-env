"""Fixed main entry point."""

import asyncio
import sys
from src.server import VoiceMCPServer
from src.config import Config

async def main() -> None:
    """Main entry point."""
    try:
        config = Config()
        server = VoiceMCPServer(config)
        await server.run()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Server failed to start: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())