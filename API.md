# Voice Assistant API Documentation

## Overview

The Voice Assistant provides both WebSocket server and client APIs for voice recognition and Claude Code integration.

## WebSocket Server API

### Connection
```
ws://localhost:8765
```

### Message Format
All messages are JSON objects with an `action` field.

### Actions

#### 1. Start Voice Capture
**Request:**
```json
{
  "action": "start_capture",
  "context": "browser|terminal",
  "timeout": 30
}
```

**Response:**
```json
{
  "type": "result",
  "text": "corrected voice text",
  "context": "browser",
  "language": "it"
}
```

**Error Response:**
```json
{
  "type": "error",
  "message": "Voice capture timeout"
}
```

#### 2. Stop Voice Capture
**Request:**
```json
{
  "action": "stop_capture"
}
```

**Response:**
```json
{
  "type": "status",
  "message": "Capture stopped"
}
```

#### 3. Set Language
**Request:**
```json
{
  "action": "set_language",
  "language": "it|en"
}
```

**Response:**
```json
{
  "type": "status",
  "message": "Language set to it"
}
```

#### 4. Get Status
**Request:**
```json
{
  "action": "get_status"
}
```

**Response:**
```json
{
  "type": "status",
  "language": "it",
  "permanent_mode": false,
  "connected_clients": 2,
  "available_languages": ["it", "en"]
}
```

## Python Client API

### ClaudeVoiceClient

#### Basic Usage
```python
import asyncio
from vosk_voice_assistant.clients import ClaudeVoiceClient

async def main():
    client = ClaudeVoiceClient()
    
    # Connect to server
    await client.connect()
    
    # Capture voice input
    text = await client.capture_voice_input(context="browser")
    
    # Use with Claude Code
    response = await client.voice_to_claude(
        template_name="explain",
        context="browser"
    )
    
    await client.disconnect()

asyncio.run(main())
```

#### Methods

##### `async connect() -> None`
Connect to the voice WebSocket server.

##### `async disconnect() -> None`
Disconnect from the voice server.

##### `async capture_voice_input(context="browser", timeout=None) -> str`
Capture voice input and return corrected text.

**Parameters:**
- `context`: "browser" or "terminal" for context-specific corrections
- `timeout`: Timeout in seconds (uses server default if None)

**Returns:** Corrected text string

**Raises:** `WebSocketError` if connection or capture fails

##### `async set_language(language: str) -> None`
Set the voice recognition language.

**Parameters:**
- `language`: "it" or "en"

##### `async get_server_status() -> dict`
Get server status information.

**Returns:** Dictionary with server status

##### `detect_current_context() -> dict[str, str]`
Detect current development context (Git branch, file types, etc.).

**Returns:** Dictionary with context information

##### `expand_prompt_template(template_name: str, **kwargs) -> str`
Expand a prompt template with context variables.

**Parameters:**
- `template_name`: Name of template ("explain", "fix", "refactor", etc.)
- `**kwargs`: Additional variables for template substitution

**Returns:** Expanded prompt string

##### `async voice_to_claude(template_name=None, context="browser", interactive=False, **kwargs) -> str`
Complete voice-to-Claude workflow.

**Parameters:**
- `template_name`: Optional template to use
- `context`: Voice context ("browser" or "terminal")
- `interactive`: Whether to run Claude in interactive mode
- `**kwargs`: Additional template variables

**Returns:** Claude Code response

#### Available Templates

- `explain`: "Explain this code: {context}"
- `fix`: "Fix this code issue: {context}"
- `refactor`: "Refactor this code: {context}"
- `optimize`: "Optimize this code: {context}"
- `test`: "Write tests for: {context}"
- `document`: "Add documentation to: {context}"
- `security`: "Review security of: {context}"
- `performance`: "Analyze performance of: {context}"

## Configuration API

### Environment Variables

```bash
# WebSocket Configuration
VOSK_WEBSOCKET__HOST=localhost          # Server host
VOSK_WEBSOCKET__PORT=8765               # Server port
VOSK_WEBSOCKET__MAX_SIZE=1048576        # Max message size

# Voice Models
VOSK_MODEL_IT=/path/to/italian/model    # Italian model path
VOSK_MODEL_EN=/path/to/english/model    # English model path

# Vosk Engine
VOSK_VOSK__SAMPLE_RATE=16000            # Audio sample rate
VOSK_VOSK__VERBOSE=false                # Verbose logging
VOSK_VOSK__BLOCK_SIZE=8000              # Audio block size

# Server Settings
VOSK_SERVER__DEFAULT_LANGUAGE=it        # Default language
VOSK_SERVER__TIMEOUT_SECONDS=30         # Operation timeout
VOSK_SERVER__MAX_CLIENTS=10             # Max concurrent clients

# Logging
VOSK_LOG_LEVEL=INFO                     # Log level
```

### Programmatic Configuration

```python
from vosk_voice_assistant.config import settings

# Access configuration
print(settings.websocket.host)
print(settings.vosk.sample_rate)
print(settings.server.default_language)

# Text correction mappings
it_terms = settings.text_correction.it_tech_terms
linux_cmds = settings.text_correction.linux_commands
```

## Text Correction API

### Functions

#### `correct_text(text: str, context: Literal["browser", "terminal"]) -> str`
Correct voice-to-text input based on context.

**Parameters:**
- `text`: Raw text from voice recognition
- `context`: Context for correction

**Returns:** Corrected text string

#### `get_available_corrections(context: Literal["browser", "terminal"]) -> dict[str, str]`
Get available corrections for a context.

**Returns:** Dictionary of corrections

### Context Types

- **Browser Context**: Applies Italian tech term corrections
  - "ghit ab" → "github"
  - "docher" → "docker"
  - "kubernet" → "kubernetes"
  - etc.

- **Terminal Context**: Applies Linux command corrections
  - "elle es" → "ls"
  - "ci di" → "cd"
  - "pi uadiblu" → "pwd"
  - etc.

## Error Handling

### Exception Hierarchy

```python
VoskVoiceAssistantError           # Base exception
├── ModelNotFoundError            # Vosk model not found
├── AudioDeviceError              # Audio device issues
├── VoskEngineError              # Vosk engine issues
├── WebSocketError               # WebSocket connection issues
└── ConfigurationError           # Configuration issues
```

### Error Responses

All API errors follow this format:
```json
{
  "type": "error",
  "message": "Descriptive error message"
}
```

Common error scenarios:
- Voice capture timeout
- Unsupported language
- Model not found
- Connection failed
- Invalid JSON format

## Examples

### Simple Voice Capture
```python
import asyncio
from vosk_voice_assistant.clients import ClaudeVoiceClient

async def simple_capture():
    client = ClaudeVoiceClient()
    text = await client.capture_voice_input()
    print(f"You said: {text}")
    await client.disconnect()

asyncio.run(simple_capture())
```

### Voice with Template
```python
async def voice_with_template():
    client = ClaudeVoiceClient()
    
    response = await client.voice_to_claude(
        template_name="explain",
        context="browser"
    )
    
    print(f"Claude explanation: {response}")
    await client.disconnect()

asyncio.run(voice_with_template())
```

### Custom Server Connection
```python
client = ClaudeVoiceClient(
    server_host="192.168.1.100",
    server_port=9000
)
```

### Error Handling
```python
from vosk_voice_assistant.exceptions import WebSocketError

try:
    await client.capture_voice_input(timeout=10)
except WebSocketError as e:
    print(f"Voice capture failed: {e}")
```