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


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    vosk: VoskConfig = Field(default_factory=VoskConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)

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
