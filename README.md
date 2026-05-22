# Music CLI & Controller

A unified YouTube Music controller featuring a Model Context Protocol (MCP) server, a robust Typer command line interface, and an ultra-premium dark-mode NiceGUI interactive dashboard.

Managed as a clean workspace using `uv`.

## 📦 System Dependency

This controller orchestrates background audio streams using the **`mpv`** media player. Ensure it is installed on your host system:

```bash
brew install mpv
```

This will automatically configure `mpv` along with the necessary `yt-dlp` stream hooks.

## 🚀 Getting Started

### 1. Synchronize the Workspace
Install the python package and dependencies into a local virtual environment:
```bash
uv sync
```

### 2. Standard CLI Usage
Query YouTube Music or control playback from the console:
```bash
# Search tracks
uv run music search "lofi hip hop"

# Search and play a track immediately
uv run music play "lofi hip hop"

# Play a track using its explicit Video ID
uv run music play-id d7G2_XwMmsU

# Check player status and track metadata
uv run music status

# Adjust volume
uv run music volume 50

# Toggle between Play and Pause states
uv run music toggle
```

### 3. Launch the NiceGUI Dashboard
Start the gorgeous real-time glassmorphic UI:
```bash
uv run music-ui
```
Open `http://localhost:8080` in your web browser.

### 4. Run the MCP Server
Launch the Model Context Protocol stdio server for developer AI agents:
```bash
uv run music-mcp
```

## 🔐 Credentials & fallbacks
- Run authentication setup with: `uv run ytmusicapi oauth`
- If running in headless or throttled cloud servers, supply a `YTM_COOKIE` environment variable containing a valid browser session cookie header.
