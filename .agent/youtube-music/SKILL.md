---
name: YouTube Music Control & Playback
description: Control YouTube Music streaming playback, check status, adjust volume, view history, search/play tracks, and manage playlists.
---

# YouTube Music Control & Playback

This skill enables your AI agent to control system music playback and interact with your YouTube Music Premium account.

## Requirements
*   **Media Player:** `mpv` must be installed on the host system (`brew install mpv`).
*   **Authentication:** Managed via `oauth.json` in the `/Users/adithya/Development/adithyasean/music-cli` directory.

## Available CLI Tools
The CLI is installed globally and can be run from any directory:

*   **Search Tracks:** `music search "<query>"`
*   **Play Song by Search:** `music play "<query>"`
*   **Play Song by Video ID:** `music play-id <video_id>`
*   **Pause/Resume Playback:** `music toggle`
*   **Stop Playback completely:** `music stop`
*   **Get Live Telemetry/Metadata:** `music status`
*   **Set Volume Level (0-100):** `music volume <percentage>`
*   **View Recent Cloud Watch History:** `music history --limit <num>`
*   **List Library Playlists:** `music playlists --limit <num>`
*   **Play a Full Playlist:** `music play-playlist <playlist_id>`

## Available MCP Tools
If the `YouTubeMusicController` MCP server is active in the environment, the following programmatic tools are available:
*   `search_tracks(query: str, limit: int = 5)` -> Search songs and return details.
*   `play_track_by_id(video_id: str)` -> Direct playback trigger.
*   `toggle_playback()` -> Toggle Pause/Play state.
*   `check_playback_status()` -> Real-time volume, track metadata, and time elapsed.
*   `stop_playback()` -> Stop audio streaming.
*   `get_recent_history(limit: int = 5)` -> Retrieve logged watch history from the premium account.
*   `list_playlists(limit: int = 25)` -> List all playlists in the user's YouTube Music library.
*   `play_playlist(playlist_id: str)` -> Load and play a full playlist by its Playlist ID.
