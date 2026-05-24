import os
import sys
import time
import subprocess
from typing import Dict, Any, List
from ytmusicapi import YTMusic
from python_mpv_jsonipc import MPV

class MusicService:
    def __init__(self, token_path: str = "oauth.json", cookie_env_var: str = "YTM_COOKIE"):
        self.ipc_socket_path = "/tmp/mpv-music.sock" if sys.platform != "win32" else r"\\.\pipe\mpv-music"
        self.player = None
        self._init_ytmusic(token_path, cookie_env_var)
        self._ensure_mpv_running()

    def _init_ytmusic(self, token_path: str, cookie_env_var: str):
        # Resolve absolute path for token_path if it's relative
        if not os.path.isabs(token_path):
            if os.path.exists(token_path):
                token_path = os.path.abspath(token_path)
            else:
                repo_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", token_path))
                if os.path.exists(repo_root_path):
                    token_path = repo_root_path
                else:
                    token_path = os.path.abspath(token_path)

        self.token_path = token_path

        # Fallback to browser cookies if running on cloud servers to bypass IP blocks
        cookie_val = os.getenv(cookie_env_var)
        if cookie_val:
            print("Initializing YTMusic with browser cookies from environment", file=sys.stderr)
            self.yt = YTMusic(auth=cookie_val)
        elif os.path.exists(token_path):
            print(f"Initializing YTMusic with OAuth credentials from {token_path}", file=sys.stderr)
            self.yt = YTMusic(auth=token_path)
        else:
            print("Initializing YTMusic anonymously (Standard Search)", file=sys.stderr)
            self.yt = YTMusic()

    def _generate_cookies_file(self) -> str:
        """Parse Cookie string from oauth.json and write it in Netscape format."""
        if not hasattr(self, "token_path") or not self.token_path or not os.path.exists(self.token_path):
            return ""

        try:
            import json
            with open(self.token_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            cookie_str = config.get("Cookie")
            if not cookie_str:
                return ""

            cookies_lines = [
                "# Netscape HTTP Cookie File",
                "# This file was generated automatically from oauth.json",
            ]

            pairs = cookie_str.split("; ")
            for pair in pairs:
                if "=" in pair:
                    name, val = pair.split("=", 1)
                    cookies_lines.append(f".youtube.com\tTRUE\t/\tTRUE\t2147483647\t{name}\t{val}")

            base_dir = os.path.dirname(os.path.abspath(self.token_path))
            cookies_txt_path = os.path.join(base_dir, "cookies.txt")
            with open(cookies_txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(cookies_lines) + "\n")

            print(f"Successfully generated Netscape cookies file at: {cookies_txt_path}", file=sys.stderr)
            return cookies_txt_path
        except Exception as e:
            print(f"Error generating cookies file: {e}", file=sys.stderr)
            return ""

    def _is_player_healthy(self) -> bool:
        """Check if the mpv player is currently responsive over the IPC socket."""
        if not self.player:
            return False
        try:
            # Query a simple property to test the round-trip IPC communication
            _ = self.player.volume
            return True
        except Exception:
            # Socket is dead or connection was closed
            try:
                self.player.close()
            except Exception:
                pass
            self.player = None
            return False

    def _ensure_mpv_running(self):
        if self._is_player_healthy():
            return

        try:
            # Check for an active instance on the IPC socket
            self.player = MPV(start_mpv=False, ipc_socket=self.ipc_socket_path)
            if not self._is_player_healthy():
                raise RuntimeError("Stale socket connection")
            print(f"Connected to existing mpv player daemon on {self.ipc_socket_path}", file=sys.stderr)
        except Exception:
            print(f"No active mpv daemon on {self.ipc_socket_path}. Spawning new process...", file=sys.stderr)
            # Spawn a new backgrounded, video-disabled, idle mpv daemon
            cookies_path = self._generate_cookies_file()
            script_dir = os.path.dirname(os.path.abspath(__file__))
            lua_script_path = os.path.join(script_dir, "auto_pause.lua")
            cmd = [
                "mpv",
                "--idle",
                "--no-video",
                "--quiet",
                f"--script={lua_script_path}",
                f"--input-ipc-server={self.ipc_socket_path}"
            ]
            # Always use cookies-from-browser=chrome to ensure we extract fresh active browser session cookies
            cmd.append("--ytdl-raw-options=cookies-from-browser=chrome")

            try:
                log_file = open("/tmp/mpv-music.log", "w", encoding="utf-8")
                subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=log_file
                )
                # Allow time for socket binding
                time.sleep(1.0)
                self.player = MPV(start_mpv=False, ipc_socket=self.ipc_socket_path)
                print("Successfully spawned and connected to new mpv daemon.", file=sys.stderr)
            except FileNotFoundError as fnf_err:
                import shutil
                if not shutil.which("mpv"):
                    print("WARNING: 'mpv' executable was not found on the system path.", file=sys.stderr)
                    print("Please ensure mpv is installed ('brew install mpv' or similar).", file=sys.stderr)
                else:
                    print(f"Socket connection retry failed. The mpv process might still be starting up: {fnf_err}", file=sys.stderr)
                self.player = None
            except Exception as e:
                print(f"ERROR starting mpv daemon: {e}", file=sys.stderr)
                self.player = None

    def search_tracks(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        # Retrieve track metadata safely
        try:
            results = self.yt.search(query, filter="songs", limit=limit)
        except Exception as e:
            print(f"ytmusicapi search error: {e}", file=sys.stderr)
            return []

        tracks = []
        for track in results:
            # Safely parse artists
            artists_list = []
            if "artists" in track and isinstance(track["artists"], list):
                for artist in track["artists"]:
                    if isinstance(artist, dict) and "name" in artist:
                        artists_list.append(artist["name"])
            artists_str = ", ".join(artists_list) if artists_list else "Unknown Artist"

            # Safely parse album
            album_name = "N/A"
            if "album" in track:
                if isinstance(track["album"], dict) and "name" in track["album"]:
                    album_name = track["album"]["name"]
                elif isinstance(track["album"], str):
                    album_name = track["album"]

            tracks.append({
                "id": track.get("videoId", ""),
                "title": track.get("title", "Unknown Track"),
                "artists": artists_str,
                "album": album_name,
                "duration": track.get("duration", "N/A")
            })
        return tracks

    def play_track(self, video_id: str):
        self._ensure_mpv_running()
        if not self.player:
            raise RuntimeError("mpv player is not running and could not be started.")

        # Resolve stream url; mpv utilizes native yt-dlp hooks
        stream_url = f"https://music.youtube.com/watch?v={video_id}"
        self.player.command("loadfile", stream_url, "replace")
        self.player.volume = 100
        self.player.pause = False

        # Log playback to YouTube Music watch history if authenticated
        try:
            if hasattr(self, "yt") and self.yt and getattr(self.yt, "auth_type", None) and self.yt.auth_type.name != "UNAUTHORIZED":
                song_data = self.yt.get_song(video_id)
                self.yt.add_history_item(song_data)
                print(f"Successfully logged play history to YouTube Music for video: {video_id}", file=sys.stderr)
        except Exception as e:
            print(f"Failed to log play history to YouTube Music: {e}", file=sys.stderr)

    def play_playlist(self, playlist_id: str):
        """Load a full YouTube Music playlist into mpv for continuous playback."""
        self._ensure_mpv_running()
        if not self.player:
            raise RuntimeError("mpv player is not running and could not be started.")

        playlist_url = f"https://music.youtube.com/playlist?list={playlist_id}"
        self.player.command("loadfile", playlist_url, "replace")
        self.player.volume = 100
        self.player.pause = False

    def toggle_pause(self) -> bool:
        self._ensure_mpv_running()
        if not self.player:
            raise RuntimeError("mpv player is not running.")
        
        new_state = not self.player.pause
        self.player.pause = new_state
        return new_state

    def stop_playback(self):
        self._ensure_mpv_running()
        if not self.player:
            raise RuntimeError("mpv player is not running.")
        self.player.command("stop")

    def get_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        if not hasattr(self, "yt") or not self.yt or not getattr(self.yt, "auth_type", None) or self.yt.auth_type.name == "UNAUTHORIZED":
            raise RuntimeError("No authenticated session available. Please configure oauth.json.")
        
        try:
            results = self.yt.get_history()
            tracks = []
            for track in results[:limit]:
                artists_list = []
                if "artists" in track and isinstance(track["artists"], list):
                    for artist in track["artists"]:
                        if isinstance(artist, dict) and "name" in artist:
                            artists_list.append(artist["name"])
                artists_str = ", ".join(artists_list) if artists_list else "Unknown Artist"

                album_name = "N/A"
                if "album" in track:
                    if isinstance(track["album"], dict) and "name" in track["album"]:
                        album_name = track["album"]["name"]
                    elif isinstance(track["album"], str):
                        album_name = track["album"]

                tracks.append({
                    "id": track.get("videoId", ""),
                    "title": track.get("title", "Unknown Track"),
                    "artists": artists_str,
                    "album": album_name,
                    "duration": track.get("duration", "N/A")
                })
            return tracks
        except Exception as e:
            print(f"ytmusicapi history error: {e}", file=sys.stderr)
            return []

    def get_playlists(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetch the authenticated user's YouTube Music library playlists."""
        if not hasattr(self, "yt") or not self.yt or not getattr(self.yt, "auth_type", None) or self.yt.auth_type.name == "UNAUTHORIZED":
            raise RuntimeError("No authenticated session available. Please configure oauth.json.")

        try:
            results = self.yt.get_library_playlists(limit=limit)
            playlists = []
            for pl in results:
                playlists.append({
                    "id": pl.get("playlistId", ""),
                    "title": pl.get("title", "Unknown Playlist"),
                    "count": pl.get("count", "N/A"),
                    "author": pl.get("author", [{}])[0].get("name", "N/A") if pl.get("author") else "N/A",
                })
            return playlists
        except Exception as e:
            print(f"ytmusicapi get_library_playlists error: {e}", file=sys.stderr)
            return []

    def set_volume(self, val: int):
        self._ensure_mpv_running()
        if not self.player:
            raise RuntimeError("mpv player is not running.")
            
        self.player.volume = max(0, min(100, val))

    def get_status(self) -> Dict[str, Any]:
        try:
            self._ensure_mpv_running()
        except Exception:
            pass
        
        if not self.player:
            return {
                "title": "Stopped",
                "artist": "N/A",
                "album": "N/A",
                "playback_time": 0.0,
                "duration": 0.0,
                "pause": True,
                "volume": 0
            }

        try:
            metadata = self.player.metadata or {}
            duration = self.player.duration
            if not duration or duration == 0.0:
                return {
                    "title": "Stopped",
                    "artist": "N/A",
                    "album": "N/A",
                    "playback_time": 0.0,
                    "duration": 0.0,
                    "pause": True,
                    "volume": self.player.volume or 0.0
                }

            return {
                "title": metadata.get("title", "Unknown Track"),
                "artist": metadata.get("artist", "Unknown Artist"),
                "album": metadata.get("album", "Unknown Album"),
                "playback_time": self.player.playback_time or 0.0,
                "duration": duration,
                "pause": self.player.pause,
                "volume": self.player.volume
            }
        except Exception:
            return {
                "title": "Stopped",
                "artist": "N/A",
                "album": "N/A",
                "playback_time": 0.0,
                "duration": 0.0,
                "pause": True,
                "volume": 0
            }

    def update_credentials(self, raw_input: str, token_path: str = "oauth.json") -> str:
        import re
        import json
        from ytmusicapi import YTMusic

        headers = {}
        raw_input = raw_input.strip()

        # Check if it looks like a curl command
        if "curl" in raw_input:
            # Match -H 'name: value' or -H "name: value"
            matches = re.findall(r'-H\s+[\'"]([^\'\"]+)[\'"]', raw_input, re.IGNORECASE)
            # Match --header 'name: value' or --header "name: value"
            matches += re.findall(r'--header\s+[\'"]([^\'\"]+)[\'"]', raw_input, re.IGNORECASE)

            for match in matches:
                if ":" in match:
                    parts = match.split(":", 1)
                    headers[parts[0].strip()] = parts[1].strip()

            # Match -b 'cookie-value' or --cookie 'cookie-value'
            cookie_matches = re.findall(r'(?:-b|--cookie)\s+[\'"]([^\'\"]+)[\'"]', raw_input, re.IGNORECASE)
            if cookie_matches:
                headers["cookie"] = cookie_matches[0]
        else:
            # Treat as raw HTTP header lines
            for line in raw_input.splitlines():
                line = line.strip()
                if not line:
                    continue
                if ":" in line:
                    parts = line.split(":", 1)
                    headers[parts[0].strip()] = parts[1].strip()

        # Check if they just pasted a raw Cookie string
        cookie = headers.get("Cookie") or headers.get("cookie")
        if not cookie and "__Secure-3PAPISID" in raw_input:
            cookie = raw_input

        if not cookie:
            raise ValueError("Could not find a valid 'Cookie' header containing '__Secure-3PAPISID' in the input.")

        user_agent = headers.get("User-Agent") or headers.get("user-agent") or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
        accept = headers.get("Accept") or headers.get("accept") or "*/*"
        accept_lang = headers.get("Accept-Language") or headers.get("accept-language") or "en-US,en;q=0.9"

        config = {
            "User-Agent": user_agent,
            "Cookie": cookie,
            "Accept": accept,
            "Accept-Language": accept_lang,
            "Origin": "https://music.youtube.com",
            "X-Origin": "https://music.youtube.com",
            "Authorization": "SAPISIDHASH"
        }

        # Write config to file
        with open(token_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # Re-initialize YTMusic on-the-fly
        self.yt = YTMusic(auth=token_path)
        return "Session updated successfully!"

