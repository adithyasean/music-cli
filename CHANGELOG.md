# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-05-24

### Added
- **`play_track`, `set_volume`, and `update_credentials` MCP Tools:** Added missing programmatic FastMCP tools to allow autonomous AI agents to search-and-play tracks, control volume level, and update YouTube Music credentials directly via MCP calls.
- **`music credentials` CLI Command:** Added a new `@app.command()` to `cli.py` to allow easy manual updating of session cookies directly from a browser Cookie header.
- **Log Rotation/Trimming Debug Logger:** Redirected standard output and standard error from the background player daemon to `/tmp/mpv-music.log` for direct visibility during troubleshooting.
- **`--quiet` Playback Mode:** Configured the background player daemon to run in `--quiet` mode to suppress stdout status progress counters, ensuring the log file stays clean and only records essential events/errors.

### Fixed
- **YouTube Bot Detection (macOS Keychain Access):** Removed the process group detachment option (`os.setpgrp`) from `subprocess.Popen` when spawning the background `mpv` player. This allows the player to securely inherit the active user's macOS login session context, enabling `yt-dlp` to successfully decrypt and use active Chrome cookies database records to stream music without bot-detection prompts.
- **"Silent Play State" Bug:** Modified the `get_status` method in `services.py` to check the track's duration. If the duration is missing or `0.0` (indicating the player is idle, stopped, or interrupted), it now cleanly returns a `Stopped` status state (`title: "Stopped"`, `artist: "N/A"`, `pause: true`, `playback_time: 0.0`) instead of returning a deceptive playing state.
- **`auto_pause.lua` Player Auto-Pause Integration:** Added a Lua script loaded by the background `mpv` daemon that automatically sets `pause = yes` on `mpv` the exact millisecond a track ends. This completely resolves the macOS menu bar icon showing a "playing" state when no song is active by ensuring the raw player pauses on idle.
- **`--macos-app-activation-policy=prohibited` Background Daemon Mode:** Configured the background `mpv` process to spawn with `prohibited` app activation policy on macOS. This completely hides `mpv` from the macOS UI, ensuring it has **no Dock icon and no Menu Bar icon**, running as a 100% silent, invisible background service.
