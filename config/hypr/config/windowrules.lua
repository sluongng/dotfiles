local colors = require("config/colors")

local rules = {
    { name = "float-pavucontrol", match = { class = [[^(org.pulseaudio.pavucontrol)]] }, float = true },
    { name = "float-picture-in-picture", match = { class = [[^()$]], title = [[^(Picture in picture)$]] }, float = true },
    { name = "float-save-file", match = { class = [[^()$]], title = [[^(Save File)$]] }, float = true },
    { name = "float-open-file", match = { class = [[^()$]], title = [[^(Open File)$]] }, float = true },
    { name = "float-librewolf-pip", match = { class = [[^(LibreWolf)$]], title = [[^(Picture-in-Picture)$]] }, float = true },
    { name = "float-blueman", match = { class = [[^(blueman-manager)$]] }, float = true },
    { name = "float-desktop-portals", match = { class = [[^(xdg-desktop-portal-gtk|xdg-desktop-portal-kde|xdg-desktop-portal-hyprland)(.*)$]] }, float = true },
    { name = "float-polkit", match = { class = [[^(polkit-gnome-authentication-agent-1|hyprpolkitagent|org.org.kde.polkit-kde-authentication-agent-1)(.*)$]] }, float = true },
    { name = "float-cachyos-hello", match = { class = [[^(CachyOSHello)$]] }, float = true },
    { name = "float-zenity", match = { class = [[^(zenity)$]] }, float = true },
    { name = "float-steam-updater", match = { class = [[^()$]], title = [[^(Steam - Self Updater)$]] }, float = true },
    { name = "opacity-file-managers", match = { class = [[^(thunar|nemo)$]] }, opacity = "0.92" },
    { name = "opacity-chat", match = { class = [[^(discord|armcord|webcord)$]] }, opacity = "0.96" },
    { name = "opacity-qq-telegram", match = { title = [[^(QQ|Telegram)$]] }, opacity = "0.95" },
    { name = "opacity-netease", match = { title = [[^(NetEase Cloud Music Gtk4)$]] }, opacity = "0.95" },
    -- The legacy rules also had a one-coordinate `move` expression. Lua's
    -- typed vec2 correctly rejects it, so retain normal compositor placement.
    { name = "picture-in-picture", match = { title = [[^(Picture-in-Picture)$]] }, float = true, size = { 960, 540 } },
    { name = "media-float", match = { title = [[^(imv|mpv|danmufloat|termfloat|nemo|ncmpcpp)$]] }, float = true, size = { 960, 540 } },
    { name = "pin-danmufloat", match = { title = [[^(danmufloat)$]] }, pin = true },
    { name = "round-float-terminals", match = { title = [[^(danmufloat|termfloat)$]] }, rounding = 5 },
    { name = "terminal-animation", match = { class = [[^(kitty|Alacritty)$]] }, animation = "slide right" },
    { name = "firefox-no-blur", match = { class = [[^(org.mozilla.firefox)$]] }, no_blur = true },
    { name = "floating-workspace-decoration", match = { float = true, workspace = "w[fv1-10]" }, border_size = 2, border_color = colors.light_blue, rounding = 8 },
    { name = "tiled-workspace-decoration", match = { float = false, workspace = "f[1-10]" }, border_size = 3, rounding = 4 },
    { name = "app-workspace-ghostty", match = { class = [[^com\.mitchellh\.ghostty$]] }, workspace = "1", focus_on_activate = true },
    { name = "app-workspace-chrome", match = { class = [[^google-chrome$]] }, workspace = "2 silent", no_initial_focus = true, focus_on_activate = true },
    { name = "app-workspace-slack", match = { class = [[^slack$]] }, workspace = "3 silent", no_initial_focus = true, suppress_event = "activate activatefocus" },
    { name = "app-workspace-discord", match = { class = [[^discord$]] }, workspace = "4 silent", no_initial_focus = true, suppress_event = "activate activatefocus" },
    { name = "app-workspace-steam", match = { class = [[^steam$]] }, workspace = "6 silent", no_initial_focus = true, suppress_event = "activate activatefocus" },
    { name = "app-workspace-slay-the-spire-2", match = { class = [[^Slay the Spire 2$]] }, workspace = "6 silent" },
    { name = "codex-app-pet-overlay", match = { class = [[^(Codex|electron)$]], title = [[^Codex$]], float = true }, pin = true, border_size = 0, rounding = 0, no_blur = true },
}

for _, rule in ipairs(rules) do
    hl.window_rule(rule)
end

hl.workspace_rule({ workspace = "w[tv1-10]", gaps_out = 0, gaps_in = 0 })
hl.workspace_rule({ workspace = "f[1]", gaps_out = 0, gaps_in = 0 })

hl.layer_rule({ name = "logout-dialog-animation", match = { namespace = "logout_dialog" }, animation = "slide top" })
hl.layer_rule({ name = "waybar-animation", match = { namespace = "waybar" }, animation = "slide down" })
hl.layer_rule({ name = "wallpaper-animation", match = { namespace = "wallpaper" }, animation = "fade 50%" })
