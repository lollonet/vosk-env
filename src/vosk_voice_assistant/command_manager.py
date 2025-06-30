"""Command management for voice CLI with external configuration."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import settings
from .exceptions import ConfigurationError
from .logging_config import get_logger

logger = get_logger(__name__)


class CommandManager:
    """
    Manages voice commands from external configuration.
    
    Loads commands from JSON configuration files and provides
    safe command execution with environment variable substitution.
    """
    
    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize command manager.
        
        Args:
            config_path: Path to commands.json file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "commands.json"
        
        self.config_path = config_path
        self.commands: Dict[str, Any] = {}
        self.allowed_directories: Dict[str, str] = {}
        self.search_settings: Dict[str, Any] = {}
        self.security_settings: Dict[str, Any] = {}
        
        self._load_configuration()
        logger.info("CommandManager initialized with %d commands", len(self.commands))
    
    def _load_configuration(self) -> None:
        """Load configuration from JSON file."""
        try:
            if not self.config_path.exists():
                raise ConfigurationError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.commands = config.get("voice_commands", {})
            self.allowed_directories = config.get("allowed_directories", {})
            self.search_settings = config.get("search_settings", {})
            self.security_settings = config.get("security_settings", {})
            
            # Expand environment variables in directory paths
            self._expand_environment_variables()
            
            logger.info("Configuration loaded successfully from %s", self.config_path)
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}") from e
    
    def _expand_environment_variables(self) -> None:
        """Expand environment variables in directory paths."""
        for key, path in self.allowed_directories.items():
            # Replace {HOME} with actual home directory
            if "{HOME}" in path:
                path = path.replace("{HOME}", str(Path.home()))
            
            # Expand other environment variables
            path = os.path.expandvars(path)
            
            self.allowed_directories[key] = path
    
    def get_safe_commands(self) -> Dict[str, List[str]]:
        """
        Get all safe commands as command name -> command list mapping.
        
        Returns:
            Dictionary of safe commands
        """
        safe_commands = {}
        for name, config in self.commands.items():
            if config.get("safe", False):
                safe_commands[name] = config["command"]
        
        return safe_commands
    
    def get_command_description(self, command_name: str) -> Optional[str]:
        """
        Get description for a command.
        
        Args:
            command_name: Name of the command
            
        Returns:
            Command description or None if not found
        """
        if command_name in self.commands:
            return self.commands[command_name].get("description")
        return None
    
    def is_safe_command(self, command_name: str) -> bool:
        """
        Check if a command is marked as safe.
        
        Args:
            command_name: Name of the command
            
        Returns:
            True if command is safe, False otherwise
        """
        if command_name in self.commands:
            return self.commands[command_name].get("safe", False)
        return False
    
    def get_allowed_directories(self) -> Dict[str, str]:
        """
        Get allowed directories with expanded paths.
        
        Returns:
            Dictionary of directory name -> path mappings
        """
        return self.allowed_directories.copy()
    
    def get_dangerous_characters(self) -> List[str]:
        """
        Get list of dangerous characters for input sanitization.
        
        Returns:
            List of dangerous characters
        """
        return self.security_settings.get("dangerous_chars", [])
    
    def get_max_input_length(self) -> int:
        """
        Get maximum allowed input length.
        
        Returns:
            Maximum input length
        """
        return self.security_settings.get("max_input_length", 100)
    
    def get_command_timeout(self) -> int:
        """
        Get command execution timeout.
        
        Returns:
            Timeout in seconds
        """
        return self.security_settings.get("command_timeout", 10)
    
    def get_max_search_query_length(self) -> int:
        """
        Get maximum search query length.
        
        Returns:
            Maximum query length
        """
        return self.search_settings.get("max_query_length", 50)
    
    def get_allowed_extensions(self) -> List[str]:
        """
        Get allowed file extensions for search.
        
        Returns:
            List of allowed extensions
        """
        return self.search_settings.get("allowed_extensions", [])
    
    def get_forbidden_paths(self) -> List[str]:
        """
        Get forbidden paths for search.
        
        Returns:
            List of forbidden paths
        """
        return self.search_settings.get("forbidden_paths", [])
    
    def add_custom_command(self, name: str, command: List[str], description: str = "", safe: bool = False) -> None:
        """
        Add a custom command at runtime.
        
        Args:
            name: Command name
            command: Command as list of strings
            description: Command description
            safe: Whether the command is safe to execute
        """
        self.commands[name] = {
            "command": command,
            "description": description,
            "safe": safe
        }
        logger.info("Added custom command: %s", name)
    
    def reload_configuration(self) -> None:
        """Reload configuration from file."""
        logger.info("Reloading configuration from %s", self.config_path)
        self._load_configuration()
    
    def get_command_list(self) -> List[str]:
        """
        Get list of all available command names.
        
        Returns:
            List of command names
        """
        return list(self.commands.keys())
    
    def get_safe_command_list(self) -> List[str]:
        """
        Get list of safe command names.
        
        Returns:
            List of safe command names
        """
        return [name for name, config in self.commands.items() if config.get("safe", False)]


# Global command manager instance
_command_manager: Optional[CommandManager] = None


def get_command_manager() -> CommandManager:
    """
    Get global command manager instance.
    
    Returns:
        CommandManager instance
    """
    global _command_manager
    if _command_manager is None:
        _command_manager = CommandManager()
    return _command_manager