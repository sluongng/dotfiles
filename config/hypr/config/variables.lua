local colors = require("config/colors")

local groupbar = {
    font_family = "Fira Sans",
    text_color = colors.dark_blue,
    col = {
        active = colors.dark_green,
        inactive = colors.light_green,
        locked_active = colors.medium_green,
        locked_inactive = colors.dark_blue,
    },
}

-- Added in 0.56. Keep the Lua config loadable by the currently running 0.55
-- session so it can be switched over before the next compositor restart.
local major, minor = hl.version():match("^(%d+)%.(%d+)")
if tonumber(major) > 0 or tonumber(minor) >= 56 then
    groupbar.disable_when_only = true
end

hl.config({
    general = {
        gaps_in = 3,
        gaps_out = 5,
        border_size = 3,
        col = {
            active_border = colors.light_green,
            inactive_border = colors.medium_blue,
        },
        layout = "dwindle",
        snap = {
            enabled = true,
        },
    },
    group = {
        col = {
            border_active = colors.dark_green,
            border_inactive = colors.light_green,
            border_locked_active = colors.medium_green,
            border_locked_inactive = colors.dark_blue,
        },
        groupbar = groupbar,
    },
    misc = {
        font_family = "Fira Sans",
        splash_font_family = "Fira Sans",
        disable_hyprland_logo = true,
        col = {
            splash = colors.light_green,
        },
        background_color = colors.dark_blue,
        enable_swallow = true,
        swallow_regex = [[^(nautilus|nemo|thunar|btrfs-assistant.)$]],
        focus_on_activate = false,
        vrr = 0,
    },
    ecosystem = {
        no_update_news = true,
        no_donation_nag = true,
    },
    render = {
        direct_scanout = false,
        send_content_type = false,
    },
    opengl = {
        nvidia_anti_flicker = true,
    },
    dwindle = {
        special_scale_factor = 0.8,
        preserve_split = true,
    },
    master = {
        new_status = "master",
        special_scale_factor = 0.8,
    },
})

hl.gesture({ fingers = 4, direction = "horizontal", action = "workspace" })
hl.gesture({ fingers = 3, direction = "down", action = "close" })
hl.gesture({ fingers = 3, direction = "up", action = "fullscreen" })
hl.gesture({ fingers = 3, direction = "left", action = "float" })
