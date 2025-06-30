"""Tests for command manager."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.vosk_voice_assistant.command_manager import CommandManager, get_command_manager
from src.vosk_voice_assistant.exceptions import ConfigurationError


class TestCommandManager:
    """Test CommandManager class."""

    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration dictionary."""
        return {
            "voice_commands": {
                "test command": {
                    "command": ["echo", "test"],
                    "description": "Test command",
                    "safe": True
                },
                "unsafe command": {
                    "command": ["rm", "-rf", "/"],
                    "description": "Dangerous command",
                    "safe": False
                }
            },
            "allowed_directories": {
                "home": "{HOME}",
                "test_dir": "/tmp/test"
            },
            "search_settings": {
                "max_query_length": 30,
                "allowed_extensions": [".txt", ".py"]
            },
            "security_settings": {
                "dangerous_chars": [";", "&"],
                "max_input_length": 50,
                "command_timeout": 5
            }
        }

    @pytest.fixture
    def config_file(self, sample_config):
        """Create a temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config, f)
            return Path(f.name)

    def test_command_manager_initialization(self, config_file):
        """Test CommandManager initialization."""
        manager = CommandManager(config_file)

        assert len(manager.commands) == 2
        assert "test command" in manager.commands
        assert "unsafe command" in manager.commands

    def test_get_safe_commands(self, config_file):
        """Test getting safe commands only."""
        manager = CommandManager(config_file)
        safe_commands = manager.get_safe_commands()

        assert len(safe_commands) == 1
        assert "test command" in safe_commands
        assert "unsafe command" not in safe_commands
        assert safe_commands["test command"] == ["echo", "test"]

    def test_environment_variable_expansion(self, config_file):
        """Test expansion of environment variables."""
        manager = CommandManager(config_file)
        directories = manager.get_allowed_directories()

        # {HOME} should be expanded to actual home directory
        assert directories["home"] == str(Path.home())
        assert directories["test_dir"] == "/tmp/test"

    def test_command_description(self, config_file):
        """Test getting command descriptions."""
        manager = CommandManager(config_file)

        assert manager.get_command_description("test command") == "Test command"
        assert manager.get_command_description("nonexistent") is None

    def test_is_safe_command(self, config_file):
        """Test checking if command is safe."""
        manager = CommandManager(config_file)

        assert manager.is_safe_command("test command") is True
        assert manager.is_safe_command("unsafe command") is False
        assert manager.is_safe_command("nonexistent") is False

    def test_security_settings(self, config_file):
        """Test getting security settings."""
        manager = CommandManager(config_file)

        assert manager.get_dangerous_characters() == [";", "&"]
        assert manager.get_max_input_length() == 50
        assert manager.get_command_timeout() == 5

    def test_search_settings(self, config_file):
        """Test getting search settings."""
        manager = CommandManager(config_file)

        assert manager.get_max_search_query_length() == 30
        assert manager.get_allowed_extensions() == [".txt", ".py"]

    def test_add_custom_command(self, config_file):
        """Test adding custom commands at runtime."""
        manager = CommandManager(config_file)

        manager.add_custom_command("custom", ["ls"], "Custom command", safe=True)

        assert "custom" in manager.commands
        assert manager.is_safe_command("custom") is True
        assert manager.get_command_description("custom") == "Custom command"

    def test_get_command_lists(self, config_file):
        """Test getting command lists."""
        manager = CommandManager(config_file)

        all_commands = manager.get_command_list()
        safe_commands = manager.get_safe_command_list()

        assert len(all_commands) == 2
        assert len(safe_commands) == 1
        assert "test command" in safe_commands
        assert "unsafe command" not in safe_commands

    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            CommandManager(Path("/nonexistent/config.json"))

    def test_invalid_json(self):
        """Test handling of invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json {")
            config_path = Path(f.name)

        with pytest.raises(ConfigurationError, match="Invalid JSON"):
            CommandManager(config_path)

    def test_reload_configuration(self, config_file, sample_config):
        """Test reloading configuration."""
        manager = CommandManager(config_file)

        # Modify configuration
        sample_config["voice_commands"]["new_command"] = {
            "command": ["echo", "new"],
            "description": "New command",
            "safe": True
        }

        with open(config_file, 'w') as f:
            json.dump(sample_config, f)

        # Reload and check
        manager.reload_configuration()
        assert "new_command" in manager.commands


class TestCommandManagerSingleton:
    """Test command manager singleton functionality."""

    def test_get_command_manager_singleton(self):
        """Test that get_command_manager returns the same instance."""
        manager1 = get_command_manager()
        manager2 = get_command_manager()

        assert manager1 is manager2

    @patch('src.vosk_voice_assistant.command_manager._command_manager', None)
    def test_get_command_manager_creates_new_instance(self):
        """Test that get_command_manager creates new instance when needed."""
        # Clear the global instance
        from src.vosk_voice_assistant import command_manager
        command_manager._command_manager = None

        manager = get_command_manager()
        assert manager is not None
        assert isinstance(manager, CommandManager)
