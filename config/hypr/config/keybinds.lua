local main_mod = "SUPER"

local function bind(keys, dispatcher, description, options)
    options = options or {}
    options.description = description
    hl.bind(keys, dispatcher, options)
end

local function exec(keys, command, description, options)
    bind(keys, hl.dsp.exec_cmd(command), description, options)
end

local ghostty_launch_queue = 0
local ghostty_launch_pending = false
local ghostty_focus_subscription
local ghostty_cleanup_timer
local launch_next_ghostty

local function finish_ghostty_launch(window)
    ghostty_launch_pending = false
    if ghostty_cleanup_timer then
        ghostty_cleanup_timer:set_enabled(false)
        ghostty_cleanup_timer = nil
    end
    if window then
        hl.timer(function()
            hl.dispatch(hl.dsp.focus({ window = window }))
        end, { timeout = 1, type = "oneshot" })
    end
    if ghostty_launch_queue > 0 then
        launch_next_ghostty()
    elseif ghostty_focus_subscription then
        if ghostty_focus_subscription:is_active() then
            ghostty_focus_subscription:remove()
        end
        ghostty_focus_subscription = nil
    end
end

launch_next_ghostty = function()
    if ghostty_launch_pending or ghostty_launch_queue == 0 then
        return
    end

    ghostty_launch_queue = ghostty_launch_queue - 1
    ghostty_launch_pending = true
    if not ghostty_focus_subscription then
        ghostty_focus_subscription = hl.on("window.open", function(window)
            if window.class ~= "com.mitchellh.ghostty" and window.initial_class ~= "com.mitchellh.ghostty" then
                return
            end
            finish_ghostty_launch(window)
        end)
    end
    ghostty_cleanup_timer = hl.timer(function()
        if ghostty_launch_pending then
            finish_ghostty_launch(nil)
        end
    end, { timeout = 3000, type = "oneshot" })

    local active_workspace = hl.get_active_workspace()
    if not active_workspace or active_workspace.id ~= 1 then
        hl.dispatch(hl.dsp.focus({ workspace = 1 }))
    end
    hl.exec_cmd([[sh -lc 'sleep 0.2; ghostty']])
end

local function open_ghostty()
    ghostty_launch_queue = ghostty_launch_queue + 1
    launch_next_ghostty()
end

local function set_gaps(gaps_out, gaps_in)
    return function()
        hl.config({ general = { gaps_out = gaps_out, gaps_in = gaps_in } })
    end
end

bind(main_mod .. " + RETURN", open_ghostty, "Open Ghostty on workspace 1")
exec(main_mod .. " + E", "dolphin", "Open Dolphin")
bind(main_mod .. " + Q", hl.dsp.window.close(), "Close the active window")
exec(main_mod .. " + SHIFT + M", [[loginctl terminate-user ""]], "Terminate the user session")
bind(main_mod .. " + V", hl.dsp.window.float({ action = "toggle" }), "Toggle floating for the active window")
exec(main_mod .. " + SPACE", "walker", "Open Walker")
bind(main_mod .. " + F", hl.dsp.window.fullscreen_state({ internal = 2, client = 0, action = "toggle" }), "Toggle compositor fullscreen")
bind(main_mod .. " + SHIFT + F", hl.dsp.window.fullscreen({ mode = "fullscreen" }), "Toggle native application fullscreen")
bind(main_mod .. " + Y", hl.dsp.window.pin(), "Pin the active window")
bind(main_mod .. " + J", hl.dsp.layout("togglesplit"), "Toggle the active window split")

exec("Print", "grimblast copy area", "Screenshot an area")
exec("CTRL + Print", "grimblast copy active", "Screenshot the active window")
exec("ALT + Print", "grimblast copy output", "Screenshot the active display")
exec(main_mod .. " + SHIFT + S", "grimblast copy area", "Screenshot an area")

bind(main_mod .. " + K", hl.dsp.group.toggle(), "Toggle grouping for the active window")

bind(main_mod .. " + SHIFT + G", set_gaps(5, 3), "Restore the default gaps")
bind(main_mod .. " + G", set_gaps(0, 0), "Remove window gaps")

local function volume_command(action)
    return action .. [[ && wpctl get-volume @DEFAULT_AUDIO_SINK@ | awk '{ if ($3 == "[MUTED]") print 0; else print int($2 * 100) }' > "/tmp/$HYPRLAND_INSTANCE_SIGNATURE.wob"]]
end

local nape_pro_keyboard_names = {
    "keychron-nape-pro-keyboard", -- Bluetooth
    "keychron-keychron-nape-pro-keyboard", -- USB / 2.4 GHz
}
local nape_pro_keyboard = { inclusive = true, list = nape_pro_keyboard_names }
local keyboards_except_nape_pro = { inclusive = false, list = nape_pro_keyboard_names }

exec("XF86AudioRaiseVolume", "ydotool mousemove --wheel -- 0 -1", "Scroll down clockwise with the Nape Pro ring", { locked = true, repeating = true, device = nape_pro_keyboard })
exec("XF86AudioLowerVolume", "ydotool mousemove --wheel -- 0 1", "Scroll up counter-clockwise with the Nape Pro ring", { locked = true, repeating = true, device = nape_pro_keyboard })
exec("XF86AudioRaiseVolume", volume_command("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), "Raise volume", { locked = true, repeating = true, device = keyboards_except_nape_pro })
exec("XF86AudioLowerVolume", volume_command("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), "Lower volume", { locked = true, repeating = true, device = keyboards_except_nape_pro })
exec("XF86AudioMute", volume_command("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), "Toggle audio mute", { locked = true, repeating = true })

exec("XF86AudioPlay", "playerctl play-pause", "Toggle play or pause")
exec("XF86AudioNext", "playerctl next", "Play the next track")
exec("XF86AudioPrev", "playerctl previous", "Play the previous track")

exec("XF86MonBrightnessUp", "brightnessctl s +5%", "Increase brightness", { locked = true, repeating = true })
exec("XF86MonBrightnessDown", "brightnessctl s 5%-", "Decrease brightness", { locked = true, repeating = true })
exec(main_mod .. " + SHIFT + L", "hyprlock", "Lock the screen")
exec(main_mod .. " + O", "killall -SIGUSR2 waybar", "Restart Waybar")
exec(main_mod .. " + B", "killall -SIGUSR1 waybar", "Toggle Waybar visibility")

local directions = {
    left = "l",
    right = "r",
    up = "u",
    down = "d",
}

for key, direction in pairs(directions) do
    bind(main_mod .. " + SHIFT + " .. key, hl.dsp.window.move({ direction = direction }), "Move the active window " .. key)
    bind(main_mod .. " + " .. key, hl.dsp.focus({ direction = direction }), "Move focus " .. key)
end

bind(main_mod .. " + mouse:272", hl.dsp.window.drag(), "Drag the active window", { mouse = true })
bind(main_mod .. " + mouse:273", hl.dsp.window.resize(), "Resize the active window", { mouse = true })

local resize_steps = {
    right = { x = 15, y = 0 },
    left = { x = -15, y = 0 },
    up = { x = 0, y = -15 },
    down = { x = 0, y = 15 },
    l = { x = 15, y = 0 },
    h = { x = -15, y = 0 },
    k = { x = 0, y = -15 },
    j = { x = 0, y = 15 },
}

bind(main_mod .. " + R", hl.dsp.submap("resize"), "Activate window resize mode")
hl.define_submap("resize", function()
    for key, delta in pairs(resize_steps) do
        bind(key, hl.dsp.window.resize({ x = delta.x, y = delta.y, relative = true }), "Resize the active window")
    end
    bind("escape", hl.dsp.submap("reset"), "Exit window resize mode")
end)

for key, delta in pairs(resize_steps) do
    bind(main_mod .. " + CTRL + SHIFT + " .. key, hl.dsp.window.resize({ x = delta.x, y = delta.y, relative = true }), "Resize the active window")
end

for workspace = 1, 10 do
    local key = workspace % 10
    bind(main_mod .. " + CTRL + " .. key, hl.dsp.window.move({ workspace = workspace, follow = true }), "Move the active window to workspace " .. workspace)
    bind(main_mod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = workspace, follow = false }), "Move the active window silently to workspace " .. workspace)
    bind(main_mod .. " + " .. key, hl.dsp.focus({ workspace = workspace }), "Switch to workspace " .. workspace)
end

bind(main_mod .. " + CTRL + left", hl.dsp.window.move({ workspace = "-1", follow = true }), "Move the active window to the previous workspace")
bind(main_mod .. " + CTRL + right", hl.dsp.window.move({ workspace = "+1", follow = true }), "Move the active window to the next workspace")

bind(main_mod .. " + PERIOD", hl.dsp.focus({ workspace = "e+1" }), "Switch to the next open workspace")
bind(main_mod .. " + COMMA", hl.dsp.focus({ workspace = "e-1" }), "Switch to the previous open workspace")
bind(main_mod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }), "Switch to the next open workspace")
bind(main_mod .. " + mouse_up", hl.dsp.focus({ workspace = "e-1" }), "Switch to the previous open workspace")
bind(main_mod .. " + slash", hl.dsp.focus({ workspace = "previous" }), "Switch to the previous workspace")
bind(main_mod .. " + minus", hl.dsp.window.move({ workspace = "special", follow = true }), "Move the active window to the special workspace")
bind(main_mod .. " + equal", hl.dsp.workspace.toggle_special("special"), "Toggle the special workspace")
bind(main_mod .. " + F1", hl.dsp.workspace.toggle_special("scratchpad"), "Toggle the scratchpad")
bind(main_mod .. " + ALT + SHIFT + F1", hl.dsp.window.move({ workspace = "special:scratchpad", follow = false }), "Move the active window silently to the scratchpad")

exec("ALT + SPACE", "fcitx5-remote -t", "Toggle Vietnamese IME")
bind(main_mod .. " + CTRL + O", function()
    hl.monitor({
        output = "HDMI-A-1",
        mode = "3840x2160@120",
        position = "0x0",
        scale = 1,
    })
    hl.dispatch(hl.dsp.dpms({ action = "on", monitor = "HDMI-A-1" }))
end, "Recover the monitor")
exec(main_mod .. " + CTRL + M", "~/.config/hypr/scripts/mx-ergo-recover recover", "Reconnect MX Ergo")
exec(main_mod .. " + CTRL + S", "~/.config/hypr/scripts/steamlink-host-mode on", "Enable Steam Link host mode")
exec(main_mod .. " + CTRL + SHIFT + S", "~/.config/hypr/scripts/steamlink-host-mode off", "Disable Steam Link host mode")
bind(main_mod .. " + Tab", hl.dsp.focus({ workspace = "e+1" }), "Switch to the next workspace")
bind(main_mod .. " + SHIFT + Tab", hl.dsp.focus({ workspace = "e-1" }), "Switch to the previous workspace")

hl.config({
    binds = {
        allow_workspace_cycles = true,
        workspace_back_and_forth = true,
        workspace_center_on = 1,
        movefocus_cycles_fullscreen = true,
        window_direction_monitor_fallback = true,
    },
})
