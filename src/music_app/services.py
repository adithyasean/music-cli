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

    def _ensure_mpv_running(self):
        try:
            # Check for an active instance on the IPC socket
            self.player = MPV(start_mpv=False, ipc_socket=self.ipc_socket_path)
            print(f"Connected to existing mpv player daemon on {self.ipc_socket_path}", file=sys.stderr)
        except Exception:
            print(f"No active mpv daemon on {self.ipc_socket_path}. Spawning new process...", file=sys.stderr)
            # Spawn a new backgrounded, video-disabled, idle mpv daemon
            cmd = [
                "mpv",
                "--idle",
                "--no-video",
                f"--input-ipc-server={self.ipc_socket_path}"
            ]
            try:
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=None if sys.platform == "win32" else os.setpgrp
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
        if not self.player:
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

    def toggle_pause(self) -> bool:
        if not self.player:
            self._ensure_mpv_running()
        if not self.player:
            raise RuntimeError("mpv player is not running.")
        
        new_state = not self.player.pause
        self.player.pause = new_state
        return new_state

    def stop_playback(self):
        if not self.player:
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

    def set_volume(self, val: int):
        if not self.player:
            self._ensure_mpv_running()
        if not self.player:
            raise RuntimeError("mpv player is not running.")
            
        self.player.volume = max(0, min(100, val))

    def get_status(self) -> Dict[str, Any]:
        if not self.player:
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
            return {
                "title": metadata.get("title", "Unknown Track"),
                "artist": metadata.get("artist", "Unknown Artist"),
                "album": metadata.get("album", "Unknown Album"),
                "playback_time": self.player.playback_time or 0.0,
                "duration": self.player.duration or 0.0,
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

