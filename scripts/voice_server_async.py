#!/usr/bin/env python3
"""
Async Voice Server - Modern WebSocket server for voice recognition.

This replaces the legacy voice_browser_server.py with a clean, async implementation.
"""

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vosk_voice_assistant.servers import start_voice_server


async def main() -> None:
    """Main entry point for the async voice server."""
    parser = argparse.ArgumentParser(description="Async Voice Server with SSL support")
    parser.add_argument("--ssl-cert", help="SSL certificate file for HTTPS support")
    parser.add_argument("--ssl-key", help="SSL private key file for HTTPS support")
    parser.add_argument("--generate-ssl", action="store_true",
                       help="Generate self-signed SSL certificates automatically")
    
    args = parser.parse_args()
    
    # Handle SSL certificate generation
    ssl_cert, ssl_key = None, None
    if args.generate_ssl:
        cert_dir = tempfile.mkdtemp()
        ssl_cert = os.path.join(cert_dir, "voice_server_cert.pem")
        ssl_key = os.path.join(cert_dir, "voice_server_key.pem")
        
        print("🔒 Generating self-signed SSL certificate...")
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", ssl_key, "-out", ssl_cert, "-days", "365", "-nodes",
            "-subj", "/C=IT/ST=Italy/L=Local/O=VoiceServer/CN=localhost",
            "-addext", "subjectAltName=DNS:localhost,DNS:127.0.0.1,IP:127.0.0.1"
        ], check=True, capture_output=True)
        print(f"✅ SSL certificate generated: {ssl_cert}")
        
    elif args.ssl_cert and args.ssl_key:
        ssl_cert, ssl_key = args.ssl_cert, args.ssl_key
    
    try:
        await start_voice_server(ssl_cert=ssl_cert, ssl_key=ssl_key)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
