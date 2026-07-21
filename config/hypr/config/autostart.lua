hl.on("hyprland.start", function()
    hl.exec_cmd("swaybg -o '*' -i /usr/share/wallpapers/cachyos-wallpapers/Skyscraper.png -m fill")
    hl.exec_cmd("waybar")
    hl.exec_cmd("fcitx5 -d")
    hl.exec_cmd("mako")
    hl.exec_cmd("nm-applet --indicator")
    hl.exec_cmd("/usr/lib/polkit-kde-authentication-agent-1")
    hl.exec_cmd([[
        wob_fifo="/tmp/$HYPRLAND_INSTANCE_SIGNATURE.wob"
        [ -p "$wob_fifo" ] || mkfifo -m 600 "$wob_fifo"
        tail -f "$wob_fifo" | wob
    ]])

    hl.exec_cmd([[systemctl --user import-environment DISPLAY WAYLAND_DISPLAY HYPRLAND_INSTANCE_SIGNATURE XDG_CURRENT_DESKTOP XDG_SESSION_TYPE XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS; command -v dbus-update-activation-environment >/dev/null 2>&1 && dbus-update-activation-environment --systemd DISPLAY WAYLAND_DISPLAY HYPRLAND_INSTANCE_SIGNATURE XDG_CURRENT_DESKTOP XDG_SESSION_TYPE XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS; systemctl --user start elephant.service; ~/.config/hypr/scripts/codex-remote-control-refresh-env]])

    hl.exec_cmd("ghostty")
    hl.exec_cmd("google-chrome-stable")
    hl.exec_cmd("slack")
    hl.exec_cmd("steam")

    -- Hypridle owns suspend-time locking. Idle-time locking remains disabled in
    -- hypridle.conf because Hyprlock can collapse Steam Remote Play framerate.
    hl.exec_cmd("hypridle")
end)
