hl.on("hyprland.start", function()
    -- exec_cmd is asynchronous. Keep initialization and client startup in one
    -- shell so portal clients cannot race the graphical-session environment.
    hl.exec_cmd([[
        "$HOME/.config/hypr/scripts/session-start" ||
            printf '%s\n' 'Session initialization failed; continuing desktop startup.' >&2

        swaybg -o '*' -i /usr/share/wallpapers/cachyos-wallpapers/Skyscraper.png -m fill &
        waybar &
        fcitx5 -d &
        mako &
        nm-applet --indicator &
        /usr/lib/polkit-kde-authentication-agent-1 &

        wob_fifo="/tmp/$HYPRLAND_INSTANCE_SIGNATURE.wob"
        [ -p "$wob_fifo" ] || mkfifo -m 600 "$wob_fifo"
        tail -f "$wob_fifo" | wob &

        ghostty &
        google-chrome-stable &
        slack &
        steam &

        # Hypridle owns suspend-time locking. Idle-time locking stays disabled
        # because Hyprlock can collapse Steam Remote Play framerate.
        hypridle &
    ]])
end)

hl.on("hyprland.shutdown", function()
    hl.exec_cmd("systemctl --user stop hyprland-session.target")
end)
