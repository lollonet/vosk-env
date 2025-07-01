"""Configuration management for Vosk Voice Assistant."""

import os
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class VoskConfig(BaseModel):
    """Configuration for Vosk engine."""

    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    model_paths: dict[str, Path] = Field(
        default_factory=lambda: {
            "it": Path(
                os.getenv(
                    "VOSK_MODEL_IT",
                    str(Path.home() / "vosk-env" / "models" / "italian"),
                )
            ),
            "en": Path(
                os.getenv(
                    "VOSK_MODEL_EN",
                    str(Path.home() / "vosk-env" / "models" / "english"),
                )
            ),
        },
        description="Paths to Vosk models by language",
    )
    verbose: bool = Field(default=False, description="Enable verbose logging")
    block_size: int = Field(default=8000, description="Audio block size")
    channels: int = Field(default=1, description="Number of audio channels")
    dtype: str = Field(default="int16", description="Audio data type")


class WebSocketConfig(BaseModel):
    """Configuration for WebSocket server."""

    host: str = Field(default="localhost", description="WebSocket server host")
    port: int = Field(default=8765, description="WebSocket server port")
    max_size: int = Field(default=1024 * 1024, description="Maximum message size")


class TextCorrectionConfig(BaseModel):
    """Configuration for text correction mappings."""

    it_tech_terms: dict[str, str] = Field(
        default_factory=lambda: {
            "ghit ab": "github",
            "git ab": "github",
            "git hub": "github",
            "docher": "docker",
            "kubernet": "kubernetes",
            "react": "react",
            "nod jes": "nodejs",
            "javascript": "javascript",
            "python": "python",
            "api": "API",
            "ei pi ai": "API",
            "rest": "REST",
        },
        description="Italian tech term corrections for browser context",
    )

    linux_commands: dict[str, str] = Field(
        default_factory=lambda: {
            "elle es": "ls",
            "liste": "ls",
            "lista": "ls",
            "liste la": "ls -la",
            "ci di": "cd",
            "vai in": "cd",
            "pi uadiblu": "pwd",
            "dove sono": "pwd",
            "tocca": "touch",
            "crea file": "touch",
            "mkdir": "mkdir",
            "copia": "cp",
            "sposta": "mv",
            "rimuovi": "rm",
            "cat": "cat",
            "mostra": "cat",
            "grep": "grep",
            "pi es": "ps",
            "processi": "ps aux",
            "top": "top",
            "df": "df -h",
            "spazio disco": "df -h",
            "free": "free -h",
            "memoria": "free -h",
            "ping": "ping",
            "wget": "wget",
            "curl": "curl",
            "git": "git",
            "git status": "git status",
            "stato git": "git status",
            "git add": "git add",
            "git commit": "git commit",
            "git push": "git push",
            "pus": "git push",
            "docker": "docker",
            "container": "docker ps",
            "sudo": "sudo",
            "installa": "sudo apt install",
        },
        description="Linux command corrections for terminal context",
    )


class ServerConfig(BaseModel):
    """Configuration for server behavior."""

    default_language: str = Field(default="it", description="Default language")
    timeout_seconds: int = Field(default=30, description="Operation timeout in seconds")
    max_clients: int = Field(default=10, description="Maximum concurrent clients")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    vosk: VoskConfig = Field(default_factory=VoskConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)
    text_correction: TextCorrectionConfig = Field(default_factory=TextCorrectionConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)

    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )

    class Config:
        env_prefix = "VOSK_"
        env_nested_delimiter = "__"


# Global settings instance
settings = Settings()
