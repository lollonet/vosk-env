# Voice Assistant Project

This project provides voice-activated functionalities using the Vosk engine with modern async architecture and Claude Code integration.

## Features

- 🎤 **Voice Recognition**: High-quality speech-to-text using Vosk engine
- 🔄 **Async Architecture**: Modern async/await implementation for optimal performance
- 🧠 **Claude Integration**: Seamless voice-to-Claude Code workflow with templates
- 🌐 **WebSocket Server**: Real-time voice processing with multiple client support
- 🔧 **Type Safety**: Comprehensive type hints and Pydantic configuration
- 🛡️ **Security**: Input validation and safe command execution
- 🌍 **Multi-language**: Support for Italian and English voice recognition

## Quick Start

### 1. Setup Environment
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Start Voice Server (New Async Implementation)
```bash
# Start the modern async WebSocket server
./scripts/voice_server_async.py
```

### 3. Use Claude Voice Client (New Async Implementation)
```bash
# Interactive mode with templates
./scripts/claude_voice_async.py

# Quick mode for single command
./scripts/claude_voice_async.py explain

# Available templates: explain, fix, refactor, optimize, test, document, security, performance
```

## Architecture Overview

### Modern Structure (Post-Refactoring)
```
src/vosk_voice_assistant/
├── servers/
│   └── websocket_server.py    # Async WebSocket server
├── clients/
│   └── claude_client.py       # Async Claude integration
├── config.py                  # Centralized Pydantic configuration
├── engine.py                  # Vosk engine wrapper
├── text_correction.py         # Context-aware text correction
├── command_manager.py          # Safe command execution
├── exceptions.py              # Custom exception hierarchy
└── logging_config.py          # Structured logging

scripts/
├── voice_server_async.py      # Modern server entry point
├── claude_voice_async.py      # Modern client entry point
└── legacy scripts...          # Original scripts (maintained for compatibility)

tests/
└── comprehensive test suite   # 32 passing tests
```

## Configuration

The project uses Pydantic for type-safe configuration with environment variable support:

```bash
# WebSocket Configuration
export VOSK_WEBSOCKET__HOST=localhost
export VOSK_WEBSOCKET__PORT=8765

# Voice Models
export VOSK_MODEL_IT=/path/to/italian/model
export VOSK_MODEL_EN=/path/to/english/model

# Server Settings
export VOSK_SERVER__DEFAULT_LANGUAGE=it
export VOSK_SERVER__TIMEOUT_SECONDS=30
```

## Usage Examples

### Voice Server
```bash
# Start async server
./scripts/voice_server_async.py

# Server features:
# - Multi-client WebSocket support
# - Context-aware text correction
# - Language switching (IT/EN)
# - Graceful error handling
```

### Claude Voice Client
```bash
# Interactive mode
./scripts/claude_voice_async.py

# Quick templates
./scripts/claude_voice_async.py explain    # Explain code
./scripts/claude_voice_async.py fix        # Fix issues
./scripts/claude_voice_async.py refactor   # Refactor code
./scripts/claude_voice_async.py test       # Write tests
```

## Development

### Code Quality
```bash
# Run tests
pytest tests/ -v

# Type checking
mypy src/

# Linting
ruff check src/ scripts/

# Auto-fix linting issues
ruff check --fix src/ scripts/
```

### Best Practices
This project follows the comprehensive guidelines in [`code-best-practice.md`](code-best-practice.md), including:
- Function size ≤ 30 lines
- Async/await for I/O operations
- Type safety with comprehensive hints
- Centralized configuration
- Modular architecture

## Migration Guide

### From Legacy to Async Architecture

**Old scripts** (still supported):
- `scripts/voice_browser_server.py` → Use `scripts/voice_server_async.py`
- `scripts/claude_voice.py` → Use `scripts/claude_voice_async.py`

**Benefits of async version**:
- Better performance and scalability
- Modern WebSocket implementation
- Type-safe configuration
- Improved error handling
- Template-based prompts

## Contributing

1. Follow the code quality guidelines in [`code-best-practice.md`](code-best-practice.md)
2. Run tests and linting before committing
3. Use conventional commit messages
4. Maintain backward compatibility when possible

## License

This project is developed for integration with Claude Code and follows modern Python best practices.
