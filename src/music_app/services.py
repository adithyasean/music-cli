import os
import sys
import time
import subprocess
import json
from typing import Dict, Any, List
from ytmusicapi import YTMusic
from python_mpv_jsonipc import MPV

class MusicService:
    def __init__(self, token_path: str = "oauth.json", cookie_env_var: str = "YTM_COOKIE"):
        self.config = self._load_config()
        self.ipc_socket_path = "/tmp/mpv-music.sock" if sys.platform != "win32" else r"\\.\pipe\mpv-music"
        self.player = None
        self._init_ytmusic(token_path, cookie_env_var)
        self._load_settings()
        if not self.use_chrome:
            self._ensure_mpv_running()

    def _load_settings(self):
        """Loads persistent user settings like playback backend."""
        settings_dir = os.path.dirname(self.token_path)
        self.settings_path = os.path.join(settings_dir, "settings.json")
        self.backend = "mpv"  # Default
        
        # Load from settings.json if it exists
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.backend = data.get("backend", "mpv").lower()
            except Exception as e:
                print(f"Error reading settings from {self.settings_path}: {e}", file=sys.stderr)
        else:
            # Fallback to YTM_USE_CHROME environment/dotenv variable
            use_chrome_env = self.config.get("YTM_USE_CHROME", "false").lower() == "true"
            self.backend = "chrome" if use_chrome_env else "mpv"

        self.use_chrome = (self.backend == "chrome")

    def set_backend(self, backend: str) -> str:
        """Saves and switches the active playback backend dynamically."""
        backend = backend.lower().strip()
        if backend not in ["chrome", "mpv"]:
            raise ValueError("Invalid backend. Supported options are 'chrome' and 'mpv'.")
        
        self.backend = backend
        self.use_chrome = (backend == "chrome")
        
        # Save to settings.json
        try:
            data = {}
            if os.path.exists(self.settings_path):
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        pass
            data["backend"] = backend
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving settings to {self.settings_path}: {e}", file=sys.stderr)
            
        # Manage active processes
        if self.use_chrome:
            # Terminate mpv if we switch to chrome to release system resources
            try:
                subprocess.run(["killall", "mpv"], capture_output=True)
            except Exception:
                pass
            return f"Playback backend successfully switched to 'chrome' (headed mode via Chrome browser). Config saved."
        else:
            # Ensure mpv is running if we switch to mpv
            self._ensure_mpv_running()
            return f"Playback backend successfully switched to 'mpv' (headless mode via background daemon). Config saved."

    def _load_config(self) -> Dict[str, str]:
        """Loads configuration variables from local, home, and standard config folders."""
        config = {}
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        possible_paths = [
            os.path.join(project_root, ".env"),
            os.path.abspath(".env"),
            os.path.expanduser("~/.env"),
            os.path.expanduser("~/.config/music-cli/.env")
        ]
        for env_path in possible_paths:
            if os.path.exists(env_path):
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#") or "=" not in line:
                                continue
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip()
                            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                                val = val[1:-1]
                            config[key] = val
                except Exception as e:
                    print(f"Error reading .env from {env_path}: {e}", file=sys.stderr)
        return config

    def _run_applescript(self, script: str) -> str:
        """Helper to execute AppleScript on macOS."""
        if sys.platform != "darwin":
            return ""
        try:
            process = subprocess.Popen(
                ['osascript', '-e', script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            if stderr.strip():
                print(f"AppleScript error: {stderr.strip()}", file=sys.stderr)
            return stdout.strip()
        except Exception as e:
            print(f"Error running AppleScript: {e}", file=sys.stderr)
            return ""

    def _execute_js_in_chrome(self, js_code: str) -> str:
        """Finds the YouTube Music tab in Chrome and runs the given JS code."""
        escaped_js = js_code.replace('"', '\\"').replace('\n', ' ')
        script = f'''
        tell application "Google Chrome"
            set found to false
            repeat with w in windows
                repeat with t in tabs of w
                    if URL of t contains "music.youtube.com" then
                        set resultVal to execute t javascript "{escaped_js}"
                        set found to true
                        return resultVal
                    end if
                end repeat
            end repeat
            if not found then
                return "NOT_OPEN"
            end if
        end tell
        '''
        return self._run_applescript(script)

    def _ensure_chrome_ytm_open(self, target_url: str = None):
        """Focuses or opens the YouTube Music tab in Google Chrome."""
        url_to_open = target_url if target_url else "https://music.youtube.com"
        script = f'''
        tell application "Google Chrome"
            set found to false
            repeat with w in windows
                set tabIdx to 1
                repeat with t in tabs of w
                    if URL of t contains "music.youtube.com" then
                        if "{target_url or ''}" is not "" then
                            set URL of t to "{url_to_open}"
                        end if
                        set active tab index of w to tabIdx
                        set index of w to 1
                        activate
                        set found to true
                        return "FOCUSED"
                    end if
                    set tabIdx to tabIdx + 1
                end repeat
            end repeat
            if not found then
                open location "{url_to_open}"
                activate
                return "OPENED"
            end if
        end tell
        '''
        return self._run_applescript(script)


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
        cookie_val = self.config.get(cookie_env_var)
        if cookie_val:
            print("Initializing YTMusic with browser cookies from environment", file=sys.stderr)
            self.yt = YTMusic(auth=cookie_val)
        elif os.path.exists(token_path):
            print(f"Initializing YTMusic with OAuth credentials from {token_path}", file=sys.stderr)
            # Try to load client credentials directly from config dictionary
            client_id = self.config.get("YTM_CLIENT_ID")
            client_secret = self.config.get("YTM_CLIENT_SECRET")
            
            # Check if this is indeed an OAuth JSON file
            is_oauth = False
            try:
                with open(token_path, "r", encoding="utf-8") as f:
                    token_data = json.load(f)
                is_oauth = all(k in token_data for k in ["access_token", "refresh_token"])
            except Exception:
                pass
                
            if is_oauth:
                if client_id and client_secret:
                    from ytmusicapi.auth.oauth import OAuthCredentials
                    oauth_creds = OAuthCredentials(client_id, client_secret)
                    self.yt = YTMusic(auth=token_path, oauth_credentials=oauth_creds)
                else:
                    print("WARNING: Custom OAuth token file detected, but YTM_CLIENT_ID and YTM_CLIENT_SECRET are not defined in your config.", file=sys.stderr)
                    self.yt = YTMusic(auth=token_path)
            else:
                self.yt = YTMusic(auth=token_path)
        else:
            print("Initializing YTMusic anonymously (Standard Search)", file=sys.stderr)
            self.yt = YTMusic()


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
            if sys.platform == "darwin":
                cmd.append("--macos-app-activation-policy=prohibited")
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
            results = self._call_yt("search", query, filter="songs", limit=limit)
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
        if self.use_chrome:
            self._ensure_chrome_ytm_open(f"https://music.youtube.com/watch?v={video_id}")
            return

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
                song_data = self._call_yt("get_song", video_id)
                self._call_yt("add_history_item", song_data)
                print(f"Successfully logged play history to YouTube Music for video: {video_id}", file=sys.stderr)
        except Exception as e:
            print(f"Failed to log play history to YouTube Music: {e}", file=sys.stderr)

    def play_playlist(self, playlist_id: str):
        """Load a full YouTube Music playlist into mpv or Chrome for continuous playback."""
        if self.use_chrome:
            self._ensure_chrome_ytm_open(f"https://music.youtube.com/playlist?list={playlist_id}")
            return

        self._ensure_mpv_running()
        if not self.player:
            raise RuntimeError("mpv player is not running and could not be started.")

        playlist_url = f"https://music.youtube.com/playlist?list={playlist_id}"
        self.player.command("loadfile", playlist_url, "replace")
        self.player.volume = 100
        self.player.pause = False

    def toggle_pause(self) -> bool:
        if self.use_chrome:
            self._execute_js_in_chrome("document.querySelector('#play-pause-button').click();")
            time.sleep(0.5)
            status = self.get_status()
            return status["pause"]

        self._ensure_mpv_running()
        if not self.player:
            raise RuntimeError("mpv player is not running.")
        
        new_state = not self.player.pause
        self.player.pause = new_state
        return new_state

    def stop_playback(self):
        if self.use_chrome:
            status = self.get_status()
            if not status["pause"]:
                self._execute_js_in_chrome("document.querySelector('#play-pause-button').click();")
            return

        self._ensure_mpv_running()
        if not self.player:
            raise RuntimeError("mpv player is not running.")
        self.player.command("stop")

    def get_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        if not hasattr(self, "yt") or not self.yt or not getattr(self.yt, "auth_type", None) or self.yt.auth_type.name == "UNAUTHORIZED":
            raise RuntimeError("No authenticated session available. Please configure oauth.json.")
        
        try:
            results = self._call_yt("get_history")
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
            err_msg = str(e)
            if "none" in err_msg.lower() or "auth" in err_msg.lower():
                print("ytmusicapi history error: The YouTube Music API returned a Server Error (likely due to expired or unauthenticated cookies in oauth.json). Attempting to run 'music credentials' or syncing Chrome cookies may resolve this.", file=sys.stderr)
            else:
                print(f"ytmusicapi history error: {e}", file=sys.stderr)
            return []

    def get_playlists(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetch the authenticated user's YouTube Music library playlists."""
        if not hasattr(self, "yt") or not self.yt or not getattr(self.yt, "auth_type", None) or self.yt.auth_type.name == "UNAUTHORIZED":
            raise RuntimeError("No authenticated session available. Please configure oauth.json.")

        try:
            results = self._call_yt("get_library_playlists", limit=limit)
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
            err_msg = str(e)
            if "none" in err_msg.lower() or "auth" in err_msg.lower():
                print("ytmusicapi playlists error: The YouTube Music API returned a Server Error (likely due to expired or unauthenticated cookies in oauth.json). Attempting to run 'music credentials' or syncing Chrome cookies may resolve this.", file=sys.stderr)
            else:
                print(f"ytmusicapi get_library_playlists error: {e}", file=sys.stderr)
            return []

    def set_volume(self, val: int):
        if self.use_chrome:
            self._execute_js_in_chrome(f"document.querySelector('ytmusic-player-bar').setVolume({val});")
            return

        self._ensure_mpv_running()
        if not self.player:
            raise RuntimeError("mpv player is not running.")
            
        self.player.volume = max(0, min(100, val))

    def get_status(self) -> Dict[str, Any]:
        status_data = self._get_raw_status()
        status_data["backend"] = self.backend
        status_data["mode"] = "headed" if self.use_chrome else "headless"
        return status_data

    def _get_raw_status(self) -> Dict[str, Any]:
        if self.use_chrome:
            js = '''
            (() => {
                const titleEl = document.querySelector('.ytmusic-player-bar .title');
                const bylineEl = document.querySelector('.ytmusic-player-bar .byline');
                const timeEl = document.querySelector('.ytmusic-player-bar .time-info');
                const playButton = document.querySelector('#play-pause-button');
                if (!titleEl) return "Stopped";
                
                let playing = false;
                if (playButton) {
                    const innerBtn = playButton.querySelector('button');
                    const label = innerBtn ? innerBtn.getAttribute('aria-label') : '';
                    playing = label === 'Pause' || playButton.getAttribute('title') === 'Pause';
                }
                
                let playbackTime = 0.0;
                let duration = 0.0;
                if (timeEl) {
                    const parts = timeEl.innerText.split('/');
                    if (parts.length === 2) {
                        const parseTime = (str) => {
                            const tParts = str.trim().split(':').map(Number);
                            if (tParts.length === 2) return tParts[0] * 60 + tParts[1];
                            if (tParts.length === 3) return tParts[0] * 3600 + tParts[1] * 60 + tParts[2];
                            return 0.0;
                        };
                        playbackTime = parseTime(parts[0]);
                        duration = parseTime(parts[1]);
                    }
                }
                
                return JSON.stringify({
                    title: titleEl.innerText,
                    artist: bylineEl ? bylineEl.innerText : 'Unknown Artist',
                    album: 'Chrome Player',
                    playback_time: playbackTime,
                    duration: duration,
                    pause: !playing,
                    volume: 100
                });
            })()
            '''
            res = self._execute_js_in_chrome(js)
            if not res or res == "NOT_OPEN" or res == "Stopped":
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
                import json
                return json.loads(res)
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

        # Parse existing cookie if it exists to preserve HttpOnly cookies like HSID, SSID
        existing_cookie_dict = {}
        if os.path.exists(token_path):
            try:
                with open(token_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    old_cookie = old_data.get("Cookie", "")
                    for part in old_cookie.split(";"):
                        part = part.strip()
                        if "=" in part:
                            k, v = part.split("=", 1)
                            existing_cookie_dict[k.strip()] = v.strip()
            except Exception:
                pass

        # Parse new cookie
        new_cookie_dict = {}
        for part in cookie.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                new_cookie_dict[k.strip()] = v.strip()

        # Merge them (new values overwrite old ones, but old keys not in new ones are preserved)
        merged_cookie_dict = {**existing_cookie_dict, **new_cookie_dict}
        cookie = "; ".join(f"{k}={v}" for k, v in merged_cookie_dict.items())

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

        # Keep or set x-goog-authuser if it was provided
        authuser = headers.get("x-goog-authuser") or headers.get("X-Goog-AuthUser")
        if not authuser and os.path.exists(token_path):
            try:
                with open(token_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    authuser = old_data.get("x-goog-authuser") or old_data.get("X-Goog-AuthUser")
            except Exception:
                pass
        if authuser:
            config["x-goog-authuser"] = authuser

        # Write config to file
        with open(token_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # Re-initialize YTMusic on-the-fly
        self.yt = YTMusic(auth=token_path)
        return "Session updated successfully!"

    def refresh_session(self) -> str:
        """Automatically refresh session credentials by decrypting Chrome's cookie database via yt-dlp."""
        cookies_file = "/tmp/yt-cookies.txt"
        if os.path.exists(cookies_file):
            try:
                os.remove(cookies_file)
            except Exception:
                pass
            
        print("Extracting cookies from Chrome database via yt-dlp...", file=sys.stderr)
        cmd = ["yt-dlp", "--cookies-from-browser", "chrome", "--cookies", cookies_file, "--skip-download", "https://music.youtube.com"]
        try:
            # We ignore errors because yt-dlp generic extractor might fail on URL, but cookies are still written
            subprocess.run(cmd, capture_output=True, timeout=10)
        except Exception as e:
            print(f"yt-dlp cookie extraction timed out or failed: {e}", file=sys.stderr)
            
        if not os.path.exists(cookies_file):
            return "Failed to extract active YouTube Music session cookies from Chrome database."
            
        try:
            cookie_parts = []
            with open(cookies_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 7:
                        domain, name, value = parts[0], parts[5], parts[6]
                        if "youtube.com" in domain:
                            cookie_parts.append(f"{name}={value}")
                            
            cookie_str = "; ".join(cookie_parts)
            
            if not cookie_str or "__Secure-3PAPISID" not in cookie_str:
                return "Failed to parse required secure cookies from extracted data."
                
            msg = self.update_credentials(cookie_str, self.token_path)
            
            # Clean up the cookies file for security
            try:
                os.remove(cookies_file)
            except Exception:
                pass
                
            return f"Session successfully synchronized with Chrome database! ({msg})"
        except Exception as e:
            return f"Failed to parse extracted cookies: {e}"

    def _call_yt(self, method_name: str, *args, **kwargs):
        """Execute a YTMusic method with automatic self-healing cookie refresh if it fails due to authentication issues."""
        # Preemptive check: sync with Chrome cookies if they changed to prevent stale requests
        try:
            script = '''
            tell application "Google Chrome"
                repeat with w in windows
                    repeat with t in tabs of w
                        if URL of t contains "music.youtube.com" then
                            return execute t javascript "document.cookie"
                        end if
                    end repeat
                end repeat
            end tell
            '''
            chrome_cookie = self._run_applescript(script)
            
            # Read current cookie from oauth.json
            current_cookie = ""
            if os.path.exists(self.token_path):
                with open(self.token_path, "r", encoding="utf-8") as f:
                    try:
                        token_data = json.load(f)
                        current_cookie = token_data.get("Cookie", "")
                    except Exception:
                        pass
            
            if chrome_cookie:
                # Parse both to compare only the keys present in chrome_cookie (since HttpOnly keys like HSID, SSID are missing from javascript)
                def parse_cookies(cookie_str):
                    res = {}
                    for part in cookie_str.split(";"):
                        part = part.strip()
                        if "=" in part:
                            k, v = part.split("=", 1)
                            res[k.strip()] = v.strip()
                    return res
                
                chrome_dict = parse_cookies(chrome_cookie)
                current_dict = parse_cookies(current_cookie)
                
                # Check if any key in chrome_cookie is different or missing in current_cookie
                cookies_changed = False
                for k, v in chrome_dict.items():
                    if current_dict.get(k) != v:
                        cookies_changed = True
                        break
                
                if cookies_changed:
                    print("Preemptive sync: Chrome cookies changed. Refreshing oauth.json...", file=sys.stderr)
                    self.update_credentials(chrome_cookie, self.token_path)
        except Exception as sync_err:
            print(f"Preemptive cookie sync failed: {sync_err}", file=sys.stderr)

        # Now execute the method
        try:
            method = getattr(self.yt, method_name)
            return method(*args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            # Catch HTTP 400 Bad Request, unauthorized, expired, 401, 403, or invalid cookie credentials, or empty/None errors
            is_auth_error = any(x in err_str for x in ["unauthorized", "login", "cookie", "auth", "credentials", "400", "401", "403", "invalid", "none"])
            
            if is_auth_error:
                print("Authentication or API error detected. Attempting self-healing cookie refresh from Chrome...", file=sys.stderr)
                refresh_msg = self.refresh_session()
                if "success" in refresh_msg.lower():
                    print("Self-healing successful! Retrying request...", file=sys.stderr)
                    method = getattr(self.yt, method_name)
                    return method(*args, **kwargs)
                else:
                    print(f"Self-healing failed: {refresh_msg}", file=sys.stderr)
            raise e

