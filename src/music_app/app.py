from nicegui import ui
import sys
from music_app.services import MusicService

service = MusicService()

def build_ui():
    # Inject Google Fonts (Outfit and Inter) and set general dark-mode container style
    ui.add_head_html('''
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Inter', sans-serif;
                background-color: #0b0c10;
                color: #e5e7eb;
            }
            .title-font {
                font-family: 'Outfit', sans-serif;
            }
            .glass-card {
                background: rgba(22, 25, 35, 0.65);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 16px;
            }
            .neon-shadow {
                box-shadow: 0 0 20px rgba(233, 30, 99, 0.15);
            }
            .glow-btn:hover {
                box-shadow: 0 0 15px rgba(233, 30, 99, 0.4);
                transform: scale(1.03);
                transition: all 0.2s ease-in-out;
            }
            /* Custom nice scrollbar */
            ::-webkit-scrollbar {
                width: 6px;
            }
            ::-webkit-scrollbar-track {
                background: #0b0c10;
            }
            ::-webkit-scrollbar-thumb {
                background: #1f2330;
                border-radius: 10px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #e91e63;
            }
        </style>
    ''')

    # Deep dark sleek theme color definitions
    ui.colors(primary='#e91e63', secondary='#880e4f', accent='#ff4081')

    # Main dashboard container with gradients
    with ui.column().classes('w-full min-h-screen bg-gradient-to-b from-slate-950 via-zinc-950 to-slate-950 p-4 sm:p-8 gap-8 items-center'):
        
        # Navigation / Header
        with ui.row().classes('w-full max-w-4xl justify-between items-center px-4 py-2 border-b border-white/5'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('music_note', color='primary').classes('text-3xl text-pink-500 animate-pulse')
                ui.label('music-cli').classes('text-2xl font-extrabold text-white tracking-wider title-font')
            ui.label('ACTIVE DAEMON').classes('text-[10px] bg-pink-500/10 text-pink-500 px-3 py-1 rounded-full font-bold border border-pink-500/20')

        # NOW PLAYING CONTAINER
        with ui.card().classes('w-full max-w-4xl p-6 glass-card neon-shadow flex flex-col md:flex-row gap-6 items-center justify-between'):
            # Left Section: Track Cover Placeholder & Text Metadata
            with ui.row().classes('items-center gap-6 w-full md:w-auto'):
                with ui.element('div').classes('w-20 h-20 rounded-xl bg-gradient-to-br from-pink-600 to-indigo-800 flex items-center justify-center shadow-lg'):
                    ui.icon('album', color='white').classes('text-4xl text-white')
                
                with ui.column().classes('gap-1'):
                    ui.label('NOW PLAYING').classes('text-[10px] font-bold text-pink-500 uppercase tracking-widest')
                    title_lbl = ui.label('Stopped').classes('text-2xl font-bold text-white leading-tight truncate w-60 sm:w-80 title-font')
                    artist_lbl = ui.label('No Active Session').classes('text-sm text-zinc-400 truncate w-60 sm:w-80')
            
            # Right Section: Real-Time Playback Telemetry
            with ui.column().classes('items-end w-full md:w-auto gap-1'):
                # Interactive Progress Bar
                progress_bar = ui.linear_progress(value=0.0).classes('w-full md:w-64 h-1.5 rounded-full overflow-hidden')
                time_lbl = ui.label('0s / 0s').classes('text-xs text-zinc-400 self-end mt-1 font-mono')

        # CONTROLS PANEL
        with ui.card().classes('w-full max-w-4xl p-6 glass-card flex flex-col sm:flex-row gap-6 items-center justify-between'):
            # Playback actions
            with ui.row().classes('items-center gap-4'):
                play_btn = ui.button(
                    on_click=lambda: service.toggle_pause()
                ).props('color=primary size=lg round shadow-lg').classes('glow-btn')
                # Initialize play button icon
                play_btn.props('icon=play_arrow')

                # Mute/Volume-off action
                ui.button(
                    on_click=lambda: volume_slider.set_value(0)
                ).props('icon=volume_off color=zinc flat round').classes('text-zinc-400 hover:text-white')

            # Volume level controls
            with ui.row().classes('items-center gap-3 w-full sm:w-auto justify-end'):
                ui.icon('volume_up', color='zinc').classes('text-zinc-400')
                volume_slider = ui.slider(
                    min=0, max=100, value=100, 
                    on_change=lambda e: service.set_volume(e.value)
                ).classes('w-36 sm:w-48')
                volume_lbl = ui.label('100%').classes('text-xs text-zinc-400 font-mono w-8 text-right')

        # SEARCH SECTION
        with ui.card().classes('w-full max-w-4xl p-6 glass-card flex flex-col gap-4'):
            ui.label('Search Tracks').classes('text-lg font-bold text-white title-font')
            
            with ui.row().classes('w-full gap-2 items-center'):
                search_input = ui.input(
                    label='Search YouTube Music...', 
                    placeholder='e.g., Chillhop Beats'
                ).classes('grow bg-slate-900/50 rounded-lg text-white border-white/5').props('darkOutlined')
                
                # Execute button
                search_btn = ui.button('Search', on_click=lambda: execute_search()).classes('h-14 px-6 glow-btn').props('color=primary shadow-lg')

            results_container = ui.column().classes('w-full mt-4 gap-2')

            async def execute_search():
                results_container.clear()
                query = search_input.value
                if not query:
                    with results_container:
                        ui.label('Please enter a query to search.').classes('text-zinc-500 text-sm')
                    return
                
                with results_container:
                    ui.spinner('dots', size='lg', color='primary').classes('mx-auto mt-4')
                
                # Run search as an async executor to prevent blocking
                loop = asyncio.get_event_loop()
                tracks = await loop.run_in_executor(None, service.search_tracks, query, 6)
                results_container.clear()
                
                with results_container:
                    if not tracks:
                        ui.label('No tracks found matching the search query.').classes('text-zinc-500 text-sm py-4')
                        return
                    for track in tracks:
                        with ui.row().classes('w-full items-center justify-between p-3 bg-white/5 border border-white/5 hover:border-pink-500/30 rounded-xl transition duration-150'):
                            with ui.row().classes('items-center gap-4'):
                                ui.icon('music_note', color='primary').classes('text-xl text-pink-500')
                                with ui.column().classes('gap-0'):
                                    ui.label(track["title"]).classes('font-bold text-sm text-white truncate w-40 sm:w-80')
                                    ui.label(f"{track['artists']} • {track['album']} ({track['duration']})").classes('text-[10px] text-zinc-400 truncate w-40 sm:w-80')
                            
                            ui.button(
                                'Play', 
                                on_click=lambda _, vid_id=track["id"]: service.play_track(vid_id)
                            ).props('flat color=primary size=sm').classes('hover:bg-pink-500/10 rounded-lg')

    # Dynamic status update loop running every second
    def update_status():
        try:
            stat = service.get_status()
            
            # Synchronize title and artist
            title_lbl.set_text(stat.get("title", "Stopped"))
            artist_lbl.set_text(stat.get("artist", "N/A"))
            
            # Sync play/pause icon button dynamically
            is_paused = stat.get("pause", True)
            play_btn.props(f'icon={"play_arrow" if is_paused else "pause"}')
            
            # Sync volume elements safely
            vol = stat.get("volume", 100)
            volume_slider.set_value(vol)
            volume_lbl.set_text(f"{int(vol)}%")
            
            # Sync playback duration details
            duration = stat.get("duration", 0.0)
            playback_time = stat.get("playback_time", 0.0)
            if duration > 0:
                progress_bar.set_value(playback_time / duration)
                time_lbl.set_text(f"{int(playback_time)}s / {int(duration)}s")
            else:
                progress_bar.set_value(0.0)
                time_lbl.set_text('0s / 0s')
        except Exception as e:
            print(f"UI telemetry pull error: {e}", file=sys.stderr)

    # Register the 1-second interval timer
    ui.timer(1.0, update_status)

# Build components at import time so NiceGUI registers them in all multiprocessing spawns
build_ui()

def main():
    # Launch NiceGUI web dashboard with reload=False to prevent multiprocessing console script issues
    print("Launching NiceGUI Web Server on Port 8080...", file=sys.stderr)
    ui.run(title="YouTube Music Controller", port=8080, native=False, show=False, reload=False)

if __name__ in {"__main__", "__mp_main__"}:
    main()
