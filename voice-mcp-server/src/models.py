from pydantic import BaseModel, field_validator
from typing import Any, Dict

class TextInput(BaseModel):
    """Validated text input model."""
    
    text: str
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text input."""
        if not v.strip():
            raise ValueError("Text cannot be empty")
        if len(v) > 10000:
            raise ValueError("Text exceeds maximum length")
        return v.strip()

class ToolResponse(BaseModel):
    """Standardized tool response."""
    
    success: bool
    message: str
    data: Dict[str, Any] = {}