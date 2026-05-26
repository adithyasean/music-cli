import sys
import json
import typer
from music_app.services import MusicService

app = typer.Typer(
    help="CLI tool to control system media playback and YouTube Music.",
    no_args_is_help=True
)
service = MusicService()

@app.command()
def search(
    query: str = typer.Argument(..., help="The search query (e.g. track title, artist name)"),
    limit: int = typer.Option(5, "--limit", "-l", help="Maximum number of results to fetch"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON data instead of formatted text.")
):
    """Search for songs on YouTube Music."""
    try:
        results = service.search_tracks(query, limit=limit)
        if json_output:
            typer.echo(json.dumps(results, indent=2))
        else:
            if not results:
                typer.echo("No tracks found.")
                return
            for index, track in enumerate(results, 1):
                typer.echo(f"{index}. [{track['id']}] {track['title']} - {track['artists']} (Album: {track['album']})")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def play(
    query: str = typer.Argument(..., help="Search query to find and play a song immediately")
):
    """Search for a song and immediately play the highest ranked match."""
    try:
        results = service.search_tracks(query, limit=1)
        if not results:
            typer.echo("No matches found.")
            raise typer.Exit(1)
        track = results[0]
        typer.echo(f"Found match: {track['title']} - {track['artists']}")
        typer.echo("Starting playback...")
        service.play_track(track["id"])
        typer.echo("Playback requested successfully.")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command(name="play-id")
def play_id(
    video_id: str = typer.Argument(..., help="The YouTube Music Video ID to play")
):
    """Play a specific song directly using its YouTube Video ID."""
    try:
        typer.echo(f"Loading track ID: {video_id}")
        service.play_track(video_id)
        typer.echo("Playback requested successfully.")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command(name="play-playlist")
def play_playlist(
    playlist_id: str = typer.Argument(..., help="The YouTube Music Playlist ID to play")
):
    """Play a full YouTube Music playlist using its Playlist ID."""
    try:
        typer.echo(f"Loading playlist ID: {playlist_id}")
        service.play_playlist(playlist_id)
        typer.echo("Playlist playback started successfully.")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def toggle():
    """Toggle the media player between Play and Pause states."""
    try:
        paused = service.toggle_pause()
        state = "PAUSED" if paused else "PLAYING"
        typer.echo(f"Player state changed to: {state}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def status():
    """Show real-time playback progress, volume level, and track metadata."""
    try:
        status_data = service.get_status()
        typer.echo(json.dumps(status_data, indent=2))
    except Exception as e:
        typer.echo(f"Error retrieving status: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def volume(
    val: int = typer.Argument(..., min=0, max=100, help="Volume percentage (0 to 100)")
):
    """Set the system media player volume."""
    try:
        service.set_volume(val)
        typer.echo(f"Volume set to {val}%")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def stop():
    """Completely stop media playback and clear the current track."""
    try:
        service.stop_playback()
        typer.echo("Playback stopped successfully.")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def history(
    limit: int = typer.Option(5, "--limit", "-l", help="Number of history items to fetch"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON data instead of formatted text.")
):
    """Retrieve and display your recently played music history from YouTube Music."""
    try:
        results = service.get_history(limit=limit)
        if json_output:
            typer.echo(json.dumps(results, indent=2))
        else:
            if not results:
                typer.echo("No recent history found.")
                return
            typer.echo("Your Recently Played YouTube Music Tracks:")
            for index, track in enumerate(results, 1):
                typer.echo(f"{index}. [{track['id']}] {track['title']} - {track['artists']} (Album: {track['album']})")
    except Exception as e:
        typer.echo(f"Error retrieving history: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def playlists(
    limit: int = typer.Option(25, "--limit", "-l", help="Maximum number of playlists to fetch"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON data instead of formatted text.")
):
    """List all playlists in your YouTube Music library."""
    try:
        results = service.get_playlists(limit=limit)
        if json_output:
            typer.echo(json.dumps(results, indent=2))
        else:
            if not results:
                typer.echo("No playlists found.")
                return
            typer.echo("Your YouTube Music Playlists:")
            for index, pl in enumerate(results, 1):
                count_str = f"{pl['count']} tracks" if pl['count'] != "N/A" else "N/A tracks"
                typer.echo(f"{index}. [{pl['id']}] {pl['title']} — {count_str}")
    except Exception as e:
        typer.echo(f"Error retrieving playlists: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def credentials(
    raw_input: str = typer.Argument(..., help="Paste the raw Cookie string or curl command from your browser")
):
    """Update your YouTube Music credentials/cookies using a browser Cookie header."""
    try:
        typer.echo("Updating credentials...")
        msg = service.update_credentials(raw_input)
        typer.echo(msg)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def backend(
    name: str = typer.Argument(..., help="The playback backend to use: 'chrome' (headed) or 'mpv' (headless)")
):
    """Switch the active playback backend between Chrome (headed) and mpv (headless)."""
    try:
        name = name.lower().strip()
        if name not in ["chrome", "mpv"]:
            typer.echo("Error: Invalid backend. Choose 'chrome' or 'mpv'.", err=True)
            raise typer.Exit(1)
        msg = service.set_backend(name)
        typer.echo(msg)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
