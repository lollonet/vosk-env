# Voice MCP Server

Minimal MCP server for text injection with quality standards.

## ✅ Quality Checklist Compliance

- **Type Hints**: Complete on all functions and methods
- **Error Handling**: Robust try/catch with specific exceptions  
- **Input Validation**: Pydantic models for all inputs
- **Logging**: Structured logging with context
- **Single Responsibility**: Each class/function has one purpose
- **No Hardcoded Values**: Configuration via Pydantic settings

## 📋 Installation

```bash
pip install -r requirements.txt
```

## 🚀 Usage

```bash
python main.py
```

## 🔧 Claude Code Configuration

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "voice-injection": {
      "command": "python",
      "args": ["main.py"],
      "cwd": "/home/claudio/GIT/vosk-env/voice-mcp-server"
    }
  }
}
```

## 🧪 Testing

### Validation Tests
- `inject_text` with `{"text": ""}` → Should fail with "Text cannot be empty"
- `inject_text` with `{"text": "A" * 20000}` → Should fail with "Text exceeds maximum length"  
- `inject_text` with `{"text": "Hello World"}` → Should succeed

### Expected Responses
- Success: `✅ Text injected successfully: Hello World...`
- Error: `❌ Error: Tool execution failed: Text cannot be empty`

## 📁 Project Structure

```
voice-mcp-server/
├── src/
│   ├── __init__.py      # Package init
│   ├── config.py        # Pydantic configuration
│   ├── models.py        # Input/output validation models
│   └── server.py        # MCP server implementation
├── main.py             # Entry point
├── requirements.txt    # Dependencies
└── README.md          # This file
```

## 🛡️ Error Handling

All tools include comprehensive error handling:
- Input validation via Pydantic models
- Structured logging with context
- Graceful failure with clear error messages
- Exception isolation and reporting