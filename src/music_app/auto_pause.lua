-- Automatically pause mpv when the final track ends or playback finishes naturally
mp.register_event("end-file", function(event)
    if event and event.reason == "eof" then
        local pos = mp.get_property_number("playlist-pos")
        local count = mp.get_property_number("playlist-count")
        if pos and count and (pos + 1 >= count) then
            mp.command("quit")
        end
    end
end)
