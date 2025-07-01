"""Async client for Claude Code integration."""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

import websockets

from ..config import settings
from ..exceptions import WebSocketError
from ..logging_config import setup_logging

# Setup logging
logger = logging.getLogger(__name__)
setup_logging()


class ClaudeVoiceClient:
    """Async client for voice input integration with Claude Code."""

    def __init__(self, server_host: Optional[str] = None, server_port: Optional[int] = None) -> None:
        """Initialize the Claude voice client."""
        self.server_host = server_host or settings.websocket.host
        self.server_port = server_port or settings.websocket.port
        self.websocket: Optional[Any] = None

        # Prompt templates for common development tasks
        self.prompt_templates = {
            "explain": "Explain this code: {context}",
            "fix": "Fix this code issue: {context}",
            "refactor": "Refactor this code: {context}",
            "optimize": "Optimize this code: {context}",
            "test": "Write tests for: {context}",
            "document": "Add documentation to: {context}",
            "security": "Review security of: {context}",
            "performance": "Analyze performance of: {context}",
        }

    async def connect(self) -> None:
        """Connect to the voice WebSocket server."""
        uri = f"ws://{self.server_host}:{self.server_port}"
        logger.info(f"Connecting to voice server at {uri}")

        try:
            self.websocket = await websockets.connect(uri)
            logger.info("Connected to voice server")
        except Exception as e:
            raise WebSocketError(f"Failed to connect to voice server: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the voice server."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("Disconnected from voice server")

    async def capture_voice_input(
        self,
        context: str = "browser",
        timeout: Optional[int] = None
    ) -> str:
        """
        Capture voice input and return corrected text.
        
        Args:
            context: Context for text correction ("browser" or "terminal")
            timeout: Timeout in seconds (uses server default if None)
            
        Returns:
            Corrected text from voice input
            
        Raises:
            WebSocketError: If connection or capture fails
        """
        if not self.websocket:
            await self.connect()

        timeout = timeout or settings.server.timeout_seconds

        request = {
            "action": "start_capture",
            "context": context,
            "timeout": timeout
        }

        try:
            await self.websocket.send(json.dumps(request))
            response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=timeout + 5  # Add buffer for server processing
            )

            data = json.loads(response)

            if data.get("type") == "error":
                raise WebSocketError(f"Voice capture error: {data.get('message')}")

            return data.get("text", "")

        except TimeoutError:
            raise WebSocketError("Voice capture timeout")
        except json.JSONDecodeError as e:
            raise WebSocketError(f"Invalid response from server: {e}")

    async def set_language(self, language: str) -> None:
        """
        Set the voice recognition language.
        
        Args:
            language: Language code ("it" or "en")
        """
        if not self.websocket:
            await self.connect()

        request = {
            "action": "set_language",
            "language": language
        }

        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        data = json.loads(response)

        if data.get("type") == "error":
            raise WebSocketError(f"Language change error: {data.get('message')}")

    async def get_server_status(self) -> dict:
        """Get server status information."""
        if not self.websocket:
            await self.connect()

        request = {"action": "get_status"}

        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        return json.loads(response)

    def detect_current_context(self) -> dict[str, str]:
        """
        Detect current development context.
        
        Returns:
            Dictionary with context information
        """
        context = {}
        current_dir = Path.cwd()

        # Git information
        context.update(self._get_git_context(current_dir))

        # File type detection
        context.update(self._get_file_context(current_dir))

        # Project type detection
        context.update(self._get_project_context(current_dir))

        return context

    def _get_git_context(self, directory: Path) -> dict[str, str]:
        """Get Git context information."""
        context = {}

        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True
            )
            context["git_branch"] = result.stdout.strip()

            # Get repository status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True
            )
            context["git_changes"] = str(len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0)

        except (subprocess.CalledProcessError, FileNotFoundError):
            context["git_branch"] = "not-git-repo"
            context["git_changes"] = "0"

        return context

    def _get_file_context(self, directory: Path) -> dict[str, str]:
        """Get file context information."""
        context = {}

        # Count files by extension
        file_counts: dict[str, int] = {}
        for file_path in directory.rglob("*"):
            if file_path.is_file() and not any(
                part.startswith('.') for part in file_path.parts
            ):
                ext = file_path.suffix.lower()
                file_counts[ext] = file_counts.get(ext, 0) + 1

        # Determine primary language
        language_mapping = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.rb': 'ruby',
            '.php': 'php'
        }

        max_count = 0
        primary_language = "unknown"
        for ext, count in file_counts.items():
            if ext in language_mapping and count > max_count:
                max_count = count
                primary_language = language_mapping[ext]

        context["primary_language"] = primary_language
        context["file_counts"] = str(file_counts)

        return context

    def _get_project_context(self, directory: Path) -> dict[str, str]:
        """Get project context information."""
        context = {}

        # Check for common project files
        project_indicators = {
            "package.json": "node",
            "requirements.txt": "python",
            "Pipfile": "python",
            "pyproject.toml": "python",
            "Cargo.toml": "rust",
            "go.mod": "go",
            "pom.xml": "java",
            "Gemfile": "ruby",
            "composer.json": "php"
        }

        for filename, project_type in project_indicators.items():
            if (directory / filename).exists():
                context["project_type"] = project_type
                break
        else:
            context["project_type"] = "unknown"

        return context

    def expand_prompt_template(self, template_name: str, **kwargs) -> str:
        """
        Expand a prompt template with context.
        
        Args:
            template_name: Name of the template to use
            **kwargs: Variables to substitute in template
            
        Returns:
            Expanded prompt string
        """
        template = self.prompt_templates.get(template_name)
        if not template:
            return f"Unknown template: {template_name}"

        # Add context information
        context_info = self.detect_current_context()
        kwargs.update(context_info)

        try:
            return template.format(**kwargs)
        except KeyError as e:
            return f"Template error - missing variable: {e}"

    async def run_claude_code(self, prompt: str, interactive: bool = False) -> str:
        """
        Run Claude Code with the given prompt.
        
        Args:
            prompt: Prompt to send to Claude Code
            interactive: Whether to run in interactive mode
            
        Returns:
            Claude Code output
        """
        cmd = ["claude-code"]
        if not interactive:
            cmd.append("--no-interactive")
        cmd.append(prompt)

        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.error(f"Claude Code error: {stderr.decode()}")
                return f"Error: {stderr.decode()}"

            return stdout.decode()

        except FileNotFoundError:
            return "Error: claude-code command not found"
        except Exception as e:
            return f"Error running Claude Code: {e}"

    async def voice_to_claude(
        self,
        template_name: Optional[str] = None,
        context: str = "browser",
        interactive: bool = False,
        **template_kwargs
    ) -> str:
        """
        Complete voice-to-Claude workflow.
        
        Args:
            template_name: Optional template to use for prompt expansion
            context: Voice context ("browser" or "terminal")
            interactive: Whether to run Claude in interactive mode
            **template_kwargs: Additional template variables
            
        Returns:
            Claude Code response
        """
        # Capture voice input
        voice_text = await self.capture_voice_input(context=context)

        if not voice_text.strip():
            return "No voice input detected"

        # Expand template if provided
        if template_name:
            template_kwargs["voice_input"] = voice_text
            prompt = self.expand_prompt_template(template_name, **template_kwargs)
        else:
            prompt = voice_text

        # Run Claude Code
        return await self.run_claude_code(prompt, interactive=interactive)


async def main() -> None:
    """Example usage of ClaudeVoiceClient."""
    client = ClaudeVoiceClient()

    try:
        # Test connection
        status = await client.get_server_status()
        print(f"Server status: {status}")

        # Capture voice and send to Claude
        result = await client.voice_to_claude(
            template_name="explain",
            context="browser"
        )
        print(f"Claude response: {result}")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
