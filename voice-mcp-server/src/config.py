from pydantic_settings import BaseSettings
from typing import Optional

class Config(BaseSettings):
    """Application configuration with validation."""
    
    server_name: str = "voice-injection"
    log_level: str = "INFO" 
    max_text_length: int = 10000
    
    model_config = {"env_prefix": "VOICE_MCP_"}