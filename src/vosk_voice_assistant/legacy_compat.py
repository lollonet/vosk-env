"""Backward compatibility layer for legacy voice CLI."""

import warnings
from pathlib import Path
from typing import Any

from .command_manager import get_command_manager
from .logging_config import get_logger

logger = get_logger(__name__)


class LegacyVoiceCliCompat:
    """
    Backward compatibility wrapper for legacy voice CLI code.

    Provides the old interface while using the new secure implementation.
    """

    def __init__(self) -> None:
        """Initialize backward compatibility layer."""
        warnings.warn(
            "Legacy voice CLI interface is deprecated. "
            "Use SecureVoiceCLI from bin/voice_cli.py instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        self.command_manager = get_command_manager()
        logger.warning("Using legacy compatibility layer - consider upgrading")

    @property
    def command_map(self) -> dict[str, str]:
        """
        Legacy command mapping (deprecated).

        Returns:
            Dictionary mapping voice commands to shell commands
        """
        warnings.warn(
            "command_map property is deprecated and unsafe. "
            "Use CommandManager.get_safe_commands() instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Return legacy format but only for safe commands
        safe_commands = self.command_manager.get_safe_commands()
        legacy_map = {}

        for name, command_list in safe_commands.items():
            # Convert list back to string (unsafe, but for compatibility)
            legacy_map[name] = " ".join(command_list)

        return legacy_map

    def process_voice_command(self, text: str) -> None:
        """
        Legacy voice command processing (deprecated).

        Args:
            text: Voice command text
        """
        warnings.warn(
            "Legacy process_voice_command is deprecated and unsafe. "
            "Use SecureVoiceCLI.process_voice_command() instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        logger.warning("Legacy voice command processing used: %s", text)

        # Redirect to secure implementation
        from bin.voice_cli import SecureVoiceCLI

        try:
            secure_cli = SecureVoiceCLI()
            secure_cli.process_voice_command(text)
        except Exception as e:
            logger.error("Error in legacy voice command processing: %s", e)
            print(f"❌ Error processing legacy command: {e}")


def migrate_legacy_config(old_command_map: dict[str, str], output_path: Path) -> None:
    """
    Migrate legacy command mapping to new JSON configuration format.

    Args:
        old_command_map: Old command mapping dictionary
        output_path: Path to save new configuration
    """
    import json

    logger.info("Migrating legacy configuration to %s", output_path)

    new_config: dict[str, Any] = {
        "voice_commands": {},
        "allowed_directories": {
            "home": "{HOME}",
            "documenti": "{HOME}/Documents",
            "download": "{HOME}/Downloads",
            "desktop": "{HOME}/Desktop",
            "radice": "/",
            "tmp": "/tmp",
        },
        "search_settings": {
            "max_query_length": 50,
            "allowed_extensions": [".txt", ".py", ".js", ".md", ".json"],
            "forbidden_paths": ["/etc", "/usr/bin", "/root"],
        },
        "security_settings": {
            "dangerous_chars": [";", "&", "|", "`", "$", "(", ")", "<", ">", '"', "'"],
            "max_input_length": 100,
            "command_timeout": 10,
        },
    }

    # Convert legacy commands
    for voice_cmd, shell_cmd in old_command_map.items():
        # Split shell command into list (basic parsing)
        command_parts = shell_cmd.split()

        # Determine if command is safe (very basic heuristic)
        safe = not any(
            dangerous in shell_cmd for dangerous in [";", "&", "|", "`", "$"]
        )

        if "voice_commands" not in new_config:
            new_config["voice_commands"] = {}
        new_config["voice_commands"][voice_cmd] = {
            "command": command_parts,
            "description": f"Legacy command: {voice_cmd}",
            "safe": safe,
        }

    # Save configuration
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(new_config, f, indent=2)

    logger.info("Legacy configuration migrated successfully")
    print(f"✅ Legacy configuration migrated to {output_path}")

    voice_commands_dict = new_config.get("voice_commands", {})
    if any(not cmd.get("safe") for cmd in voice_commands_dict.values()):
        print(
            "⚠️  Some commands were marked as unsafe - review the configuration manually"
        )


# Provide legacy import compatibility
VoiceCLI = LegacyVoiceCliCompat
