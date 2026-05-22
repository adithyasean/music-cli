import sys
import asyncio
from fastmcp import FastMCP
from music_app.services import MusicService

# Initialize the MCP Server with our brand name
mcp = FastMCP("YouTubeMusicController")
service = MusicService()

@mcp.tool()
async def search_tracks(query: str, limit: int = 5) -> str:
    """
    Search YouTube Music for tracks matching the query.
    Returns a human-readable list of matching songs with their IDs.
    """
    try:
        print(f"MCP Tool 'search_tracks' called with query='{query}', limit={limit}", file=sys.stderr)
        tracks = service.search_tracks(query, limit=limit)
        if not tracks:
            return "No tracks match the query."
        output = []
        for index, track in enumerate(tracks, 1):
            output.append(
                f"{index}. {track['title']} by {track['artists']} [Album: {track['album']}] (ID: {track['id']})"
            )
        return "\n".join(output)
    except Exception as e:
        print(f"Error encountered during search: {e}", file=sys.stderr)
        return f"Error executing search tool: {str(e)}"

@mcp.tool()
async def play_track_by_id(video_id: str) -> str:
    """
    Play a track immediately using its YouTube Video ID.
    """
    try:
        print(f"MCP Tool 'play_track_by_id' called with video_id='{video_id}'", file=sys.stderr)
        service.play_track(video_id)
        # Give a small delay to let mpv load the stream and parse metadata
        await asyncio.sleep(0.8)
        status = service.get_status()
        return f"Successfully playing: {status['title']} by {status['artist']}"
    except Exception as e:
        print(f"Error starting playback: {e}", file=sys.stderr)
        return f"Error starting playback: {str(e)}"

@mcp.tool()
async def toggle_playback() -> str:
    """
    Toggle between play and pause states.
    """
    try:
        print("MCP Tool 'toggle_playback' called", file=sys.stderr)
        paused = service.toggle_pause()
        state = "Paused" if paused else "Resumed"
        return f"Playback successfully changed to: {state}."
    except Exception as e:
        print(f"Error toggling playback: {e}", file=sys.stderr)
        return f"Error toggling playback: {str(e)}"

@mcp.tool()
async def check_playback_status() -> str:
    """
    Query the active system media player for real-time metadata, time position, volume, and pause state.
    """
    try:
        print("MCP Tool 'check_playback_status' called", file=sys.stderr)
        status = service.get_status()
        if status["title"] == "Stopped":
            return "No audio is currently playing or player is stopped."
        
        progress = f"{int(status['playback_time'])}s / {int(status['duration'])}s"
        state = "Paused" if status["pause"] else "Playing"
        return (
            f"Status: {state}\n"
            f"Track: {status['title']}\n"
            f"Artist: {status['artist']}\n"
            f"Album: {status['album']}\n"
            f"Progress: {progress}\n"
            f"Volume: {status['volume']}%"
        )
    except Exception as e:
        print(f"Error retrieving playback status: {e}", file=sys.stderr)
        return f"Error retrieving playback status: {str(e)}"

def main():
    mcp.run()

if __name__ == "__main__":
    main()
