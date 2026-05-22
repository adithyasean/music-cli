# Music CLI & Controller

A unified YouTube Music controller featuring a Model Context Protocol (MCP) server, a robust Typer command line interface, and an ultra-premium dark-mode NiceGUI interactive dashboard.

Managed as a clean workspace using `uv`.

## 📦 System Dependency

This controller orchestrates background audio streams using the **`mpv`** media player. Ensure it is installed on your host system:

```bash
brew install mpv
```

This will automatically configure `mpv` along with the necessary `yt-dlp` stream hooks.

## 🚀 Getting Started & Installation

Choose one of the following execution modes:

### Option A: Global CLI & Tool Installation (Highly Recommended)
You can install this project globally in an isolated environment. This puts the `music` (CLI), `music-mcp` (MCP Server), and `music-ui` (NiceGUI Dashboard) commands directly into your system PATH, allowing you to run them from **any directory** without `uv run` prefixes:

```bash
# Install globally in editable mode
uv tool install --editable .
```

Now you can run commands directly from anywhere:
* `music status`
* `music-ui`
* `music-mcp`

---

### Option B: Local Project Execution
If you prefer running commands strictly inside the local project directory:

1. Sync the project environment:
   ```bash
   uv sync
   ```

2. Prefix all commands with `uv run`:
   * `uv run music status`
   * `uv run music-ui`
   * `uv run music-mcp`

---

## 🛠️ CLI Usage Guide
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

# Stop playback completely
uv run music stop

# Retrieve your recently played history from YouTube Music
uv run music history --limit 5

# List all playlists in your YouTube Music library
uv run music playlists

# Play a full playlist by its Playlist ID
uv run music play-playlist <playlist_id>
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
