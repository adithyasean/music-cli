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

# Check player status, track metadata, and active backend mode
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

## 🔐 Credentials & Authentication

To interact with private endpoints (like fetching your play history, playlists, or logging played items):

1. **Initial Setup / Manual Update**:
   - Open [music.youtube.com](https://music.youtube.com/) in Google Chrome and ensure you are logged in.
   - Open Developer Tools (`Cmd + Option + I`), select the **Network** tab, click any request (like `browse`), and copy the value of the `Cookie` header.
   - Save your credentials by running:
     ```bash
     music credentials "<pasted cookie string>"
     ```
2. **Automated Background Refresh**:
   - The application automatically handles session refreshes. Whenever status queries run on macOS, it grabs fresh session cookies from Chrome in the background.
   - It **merges** these cookies with your saved configuration, ensuring that security-sensitive `HttpOnly` keys (like `HSID` and `SSID`) are preserved so your session doesn't get invalidated.
   - If a request fails due to an auth issue, a self-healing block will attempt to sync cookies and retry the request automatically.

## 🌐 macOS Google Chrome Playback Mode (Zero CLI Dependencies)

On macOS, you can route all audio playback, volume controls, and track queries directly through your active, already-logged-in **Google Chrome** browser window. This utilizes your existing Google session context, completely bypassing any bot-detection blocks and avoiding the need for `mpv` player processes.

### Setup & Activation:
1. **Enable AppleScript in Chrome:**
   - In Google Chrome, go to the top menu bar: **View ➔ Developer ➔ check "Allow JavaScript from Apple Events"**.
2. **Activate the Backend:**
   - Set the environment variable:
     ```bash
     export YTM_USE_CHROME=true
     ```
   - (Or add `YTM_USE_CHROME=true` to your project's `.env` file.)
3. All commands (`music play`, `music status`, etc.) will now control and inspect your open Google Chrome tab seamlessly!
