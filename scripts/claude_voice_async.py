#!/usr/bin/env python3
"""
Async Claude Voice Client - Modern voice integration with Claude Code.

This replaces the legacy claude_voice.py with a clean, async implementation.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vosk_voice_assistant.clients import ClaudeVoiceClient


async def interactive_mode() -> None:
    """Run in interactive mode for multiple voice commands."""
    client = ClaudeVoiceClient()

    print("🎤 Claude Voice Assistant (Async)")
    print("Available templates: explain, fix, refactor, optimize, test, document, security, performance")
    print("Type 'quit' to exit\n")

    try:
        await client.connect()
        status = await client.get_server_status()
        print(f"Connected to server - Language: {status.get('language', 'unknown')}")

        while True:
            print("\nOptions:")
            print("1. Voice input (raw)")
            print("2. Voice input with template")
            print("3. Set language")
            print("4. Show status")
            print("5. Quit")

            choice = input("\nSelect option (1-5): ").strip()

            if choice == "1":
                await handle_raw_voice_input(client)
            elif choice == "2":
                await handle_template_voice_input(client)
            elif choice == "3":
                await handle_language_change(client)
            elif choice == "4":
                await handle_show_status(client)
            elif choice == "5":
                break
            else:
                print("Invalid option. Please select 1-5.")

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect()


async def handle_raw_voice_input(client: ClaudeVoiceClient) -> None:
    """Handle raw voice input without template."""
    print("\n🎤 Speak now (30 second timeout)...")

    try:
        result = await client.voice_to_claude(context="browser")
        print(f"\n📝 Claude Response:\n{result}")
    except Exception as e:
        print(f"Error: {e}")


async def handle_template_voice_input(client: ClaudeVoiceClient) -> None:
    """Handle voice input with template expansion."""
    templates = ["explain", "fix", "refactor", "optimize", "test", "document", "security", "performance"]

    print("\nAvailable templates:")
    for i, template in enumerate(templates, 1):
        print(f"{i}. {template}")

    try:
        choice = int(input("\nSelect template (1-8): ")) - 1
        if 0 <= choice < len(templates):
            template_name = templates[choice]
            print(f"\n🎤 Speak now for '{template_name}' template (30 second timeout)...")

            # Get current context
            context_info = client.detect_current_context()
            print(f"Context: {context_info.get('primary_language', 'unknown')} project")

            result = await client.voice_to_claude(
                template_name=template_name,
                context="browser"
            )
            print(f"\n📝 Claude Response:\n{result}")
        else:
            print("Invalid template selection.")
    except ValueError:
        print("Invalid input. Please enter a number.")
    except Exception as e:
        print(f"Error: {e}")


async def handle_language_change(client: ClaudeVoiceClient) -> None:
    """Handle language change."""
    print("\nAvailable languages:")
    print("1. Italian (it)")
    print("2. English (en)")

    try:
        choice = input("Select language (1-2): ").strip()
        language = "it" if choice == "1" else "en" if choice == "2" else None

        if language:
            await client.set_language(language)
            print(f"Language changed to {language}")
        else:
            print("Invalid language selection.")
    except Exception as e:
        print(f"Error changing language: {e}")


async def handle_show_status(client: ClaudeVoiceClient) -> None:
    """Show server status."""
    try:
        status = await client.get_server_status()
        print("\n📊 Server Status:")
        print(f"Language: {status.get('language', 'unknown')}")
        print(f"Connected clients: {status.get('connected_clients', 0)}")
        print(f"Available languages: {status.get('available_languages', [])}")
        print(f"Permanent mode: {status.get('permanent_mode', False)}")
    except Exception as e:
        print(f"Error getting status: {e}")


async def quick_mode(template: str = None) -> None:
    """Run in quick mode for single voice command."""
    client = ClaudeVoiceClient()

    try:
        print("🎤 Quick mode - Speak now...")

        if template:
            result = await client.voice_to_claude(
                template_name=template,
                context="browser"
            )
        else:
            result = await client.voice_to_claude(context="browser")

        print(f"\n📝 Claude Response:\n{result}")

    except Exception as e:
        print(f"Error: {e}")


async def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1:
        # Quick mode with optional template
        template = sys.argv[1] if sys.argv[1] in [
            "explain", "fix", "refactor", "optimize",
            "test", "document", "security", "performance"
        ] else None
        await quick_mode(template)
    else:
        # Interactive mode
        await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
