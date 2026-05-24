-- Automatically pause mpv when a track ends or playback finishes
mp.register_event("end-file", function()
    mp.set_property("pause", "yes")
end)
