# Vosk Voice Assistant - Project Memory

## Quality Analysis Summary (2025-07-03)

### Overall Grade: B+ (Good with Notable Strengths)

**Excellent adherence to code-best-practice.md** with strong architectural patterns and modern Python practices.

### Key Strengths
- Process isolation architecture preventing crashes
- Strong type safety and documentation
- Modern async/await patterns
- Excellent security practices
- Clean separation of concerns

### Critical Gaps to Address Later
1. **Missing test suite** - No unit/integration tests found
2. **Function size violations** - Some functions exceed 30-line limit
   - `engine.py:start_listening()` - 82 lines
   - `websocket_server.py` methods too long
3. **Error handling** - Some bare `except:` clauses need specificity

### Architecture Highlights
- **SSL WebSocket server** with certificate generation
- **Vosk crash protection** via multiprocessing isolation
- **Context-aware text correction** (browser/terminal)
- **Comprehensive configuration** with Pydantic v2

### Recent Releases
- v1.0-ssl-fixes: SSL certificate and WebSocket connection fixes
- v2.0-crash-protection: Process isolation for Vosk assertion errors

### Test Coverage Priority
- Unit tests for VoskEngine, VoiceWebSocketServer
- Integration tests for WebSocket endpoints
- Mock Vosk engine for testing

---

## Chrome Plugin Integration Guide

### Overview
The voice system uses **Tampermonkey/Greasemonkey userscripts** that run on any webpage to provide voice input functionality via floating buttons.

### Available Userscripts

1. **`voice-input-fixed.user.js`** (Latest/Recommended)
   - Advanced version with SSL support and language switching
   - Features: WSS/WS auto-detection, reconnection logic, IT text correction
   - Buttons: Main voice toggle + Language switch button
   - Hotkeys: `Ctrl+/` (toggle voice), `Ctrl+?` (switch language), `Esc` (force off)

2. **`voice-input-toggle.user.js`** (Basic)
   - Simpler version with basic toggle functionality
   - Single button voice control with permanent mode
   - Auto language detection

### How It Works

**Server Connection:**
- Connects to WebSocket server at `localhost:8765`
- Auto-detects SSL (WSS for HTTPS sites, WS for HTTP)
- Automatic reconnection with fallback to WS if WSS fails
- Connection status feedback with visual indicators

**UI Elements:**
- **Main Button**: 🎤 (ready), 🔥 (active), 🔴 (listening), 📵 (disconnected)
- **Language Button**: IT/EN indicator with switching capability
- **Visual Feedback**: Element highlighting, correction notifications, status messages

**Voice Input Flow:**
1. Click in text field (input, textarea, contentEditable)
2. Click voice button or press `Ctrl+/` to activate
3. Speak - button turns red during listening
4. Text appears automatically in the focused field
5. IT terms get corrected automatically (browser context)

**Permanent Mode:**
- Toggle ON/OFF rather than single captures
- Continuous voice input until disabled
- Auto-restart after each successful recognition
- Follows focus changes between input fields

### Installation & Usage

**Install:**
1. Install Tampermonkey/Greasemonkey browser extension
2. Open `voice-input-fixed.user.js` in browser
3. Tampermonkey will prompt to install the script

**Enable/Disable:**
- **Tampermonkey Dashboard**: Click extension → Dashboard → toggle script on/off
- **Per-site**: Click Tampermonkey icon → toggle for current site
- **Temporary**: Press `Esc` to force disable voice input

**Testing:**
- Use `test_voice_local.html` for connection and functionality testing
- Toggle SSL/non-SSL connection testing
- Real-time connection status and message logging

### Connection Troubleshooting

**HTTPS Sites (WSS):**
- May need to accept SSL certificate at `https://localhost:8765`
- Browser may block mixed content (WSS → WS fallback)
- Script shows helpful error messages with links

**HTTP Sites (WS):**
- Direct WebSocket connection, usually works immediately
- No SSL certificate issues

**Visual Status Indicators:**
- 🔄 Blue pulsing: Connecting
- 🎤 Green: Ready for voice input  
- 🔥 Orange: Voice input active (permanent mode)
- 🔴 Red pulsing: Currently listening
- 📵 Gray: Disconnected from server

---

## MCP Server Implementation

### Voice MCP Server
- **Location**: `voice-mcp-server/` directory
- **Purpose**: Text injection MCP server for Claude Code integration
- **Implementation**: MCP 1.0.0 compatible server with proper initialization

### Features
- **Input Validation**: Pydantic models with 10,000 char limit
- **Error Handling**: Comprehensive error catching and logging
- **Tool Registration**: Single `inject_text` tool with JSON schema
- **Structured Logging**: Loguru-based logging with timestamps

### Usage
```bash
cd voice-mcp-server
python main.py  # Starts MCP server on stdio
```

### Quality Status
- ✅ MCP 1.10.1 compatibility implemented
- ✅ Server startup and configuration working
- ✅ Clean error handling and logging to stderr
- ✅ Input validation with Pydantic v2 (10,000 char limit)
- ✅ Modern async/await patterns
- ⚠️ MCP protocol handlers need debugging (tools/list and tools/call return "Invalid request parameters")

### Test Results
**✅ Working Components:**
- Server initialization and startup (no crashes)
- Configuration loading with environment variable support
- Input validation rejecting oversized text (>10K chars)
- Structured logging properly routed to stderr
- Pydantic v2 models and BaseSettings integration

**⚠️ Known Issues:**
- MCP protocol handler registration has parameter mismatch
- Both `tools/list` and `tools/call` return JSON-RPC error -32602
- May require handler signature updates for MCP 1.10.1 compliance

**🎯 Ready for Integration:**
The core server architecture is solid and ready for Claude Code integration once the MCP protocol handlers are fixed.