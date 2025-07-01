import re

with open("scripts/voice_browser_server.py") as f:
    content = f.read()

# Fix function signature
content = re.sub(
    r"async def register_client\(self, websocket\):",
    "async def register_client(self, websocket, path):",
    content,
)

with open("scripts/voice_browser_server.py", "w") as f:
    f.write(content)
