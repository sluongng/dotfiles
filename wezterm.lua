local wezterm = require 'wezterm'

-- -- The filled in variant of the < symbol
-- local SOLID_LEFT_ARROW = utf8.char(0xe0b2)
-- -- The filled in variant of the > symbol
-- local SOLID_RIGHT_ARROW = utf8.char(0xe0b0)
-- 
-- wezterm.on(
--   'format-tab-title',
--   function(tab, tabs, panes, config, hover, max_width)
--     local edge_background = '#0b0022'
--     local background = '#1b1032'
--     local foreground = '#808080'
-- 
--     if tab.is_active then
--       background = '#2b2042'
--       foreground = '#c0c0c0'
--     elseif hover then
--       background = '#3b3052'
--       foreground = '#909090'
--     end
-- 
--     local edge_foreground = background
-- 
--     -- ensure that the titles fit in the available space,
--     -- and that we have room for the edges.
--     local title = wezterm.truncate_right(tab.active_pane.title, max_width - 2)
-- 
--     return {
--       { Background = { Color = edge_background } },
--       { Foreground = { Color = edge_foreground } },
--       { Text = SOLID_LEFT_ARROW },
--       { Background = { Color = background } },
--       { Foreground = { Color = foreground } },
--       { Text = title },
--       { Background = { Color = edge_background } },
--       { Foreground = { Color = edge_foreground } },
--       { Text = SOLID_RIGHT_ARROW },
--     }
--   end
-- )

return {
    -- Font configs
    font = wezterm.font {
        family = 'Hack Nerd Font',
    },
    font_size = 11.0,


    -- System configs
    check_for_updates = false,
    animation_fps = 1,
    cursor_blink_ease_in = 'Constant',
    cursor_blink_ease_out = 'Constant',
    cursor_blink_rate = 0,
    native_macos_fullscreen_mode = true,
    window_padding = {
        left = 0,
        right = 0,
        top = 0,
        bottom = 0,
    },

    -- Tab bar style
    tab_bar_at_bottom = true,
    hide_tab_bar_if_only_one_tab = true,

    leader = { 
        -- key = 'b',
        key = 'a',
        mods = 'CTRL',
        timeout_milliseconds = 1000,
    },
    keys = {
        -- Send 'CTRL-b' to the terminal when pressing CTRL-b, CTRL-b
        -- { key = 'b', mods = 'LEADER|CTRL',     action = wezterm.action.SendString '\x02' },
        { key = 'a', mods = 'LEADER|CTRL',     action = wezterm.action.SendString '\x02' },
        { key = 'f', mods = 'CMD|CTRL', action = wezterm.action.ToggleFullScreen },


        -- **Screen management**
        { key = 'c', mods = 'LEADER', action = wezterm.action.SpawnTab 'CurrentPaneDomain' },
        { key = 'p', mods = 'LEADER', action = wezterm.action.ActivateTabRelative(-1) },
        { key = 'n', mods = 'LEADER', action = wezterm.action.ActivateTabRelative(1) },
        { key = 'o', mods = 'LEADER', action = wezterm.action.ActivatePaneDirection 'Next' },
        { key = 'l', mods = 'LEADER', action = wezterm.action.SplitHorizontal {domain = 'CurrentPaneDomain'} },
        { key = 'j', mods = 'LEADER', action = wezterm.action.SplitVertical {domain = 'CurrentPaneDomain'} },

        -- Quick open http links using Ctrl + Shift + E
        {
            key="e", mods="CTRL|SHIFT",
            action=wezterm.action{QuickSelectArgs={
                patterns={
                   "https?://\\S+"
                },
                action = wezterm.action_callback(function(window, pane)
                   local url = window:get_selection_text_for_pane(pane)
                   wezterm.log_info("opening: " .. url)
                   wezterm.open_with(url)
                end)
            }}
        },

        -- Close current pane
        {key = 'w', mods = 'CMD', action = wezterm.action.CloseCurrentPane { confirm = true } },

        -- **Editor/Shell navigations**
        { key = 'a', mods = 'SUPER', action = wezterm.action{SendString = '\x1ba'} },
        { key = 'b', mods = 'SUPER', action = wezterm.action{SendString = '\x1bb'} },
        -- leave CMD + C for copy
        -- { key = 'c', mods = 'SUPER', action = wezterm.action{SendString = '\x1bc'} },
        { key = 'd', mods = 'SUPER', action = wezterm.action{SendString = '\x1bd'} },
        { key = 'e', mods = 'SUPER', action = wezterm.action{SendString = '\x1be'} },
        { key = 'f', mods = 'SUPER', action = wezterm.action{SendString = '\x1bf'} },
        { key = 'g', mods = 'SUPER', action = wezterm.action{SendString = '\x1bg'} },
        { key = 'h', mods = 'SUPER', action = wezterm.action{SendString = '\x1bh'} },
        { key = 'i', mods = 'SUPER', action = wezterm.action{SendString = '\x1bi'} },
        { key = 'j', mods = 'SUPER', action = wezterm.action{SendString = '\x1bj'} },
        { key = 'k', mods = 'SUPER', action = wezterm.action{SendString = '\x1bk'} },
        { key = 'l', mods = 'SUPER', action = wezterm.action{SendString = '\x1bl'} },
        { key = 'm', mods = 'SUPER', action = wezterm.action{SendString = '\x1bm'} },
        { key = 'n', mods = 'SUPER', action = wezterm.action{SendString = '\x1bn'} },
        { key = 'o', mods = 'SUPER', action = wezterm.action{SendString = '\x1bo'} },
        { key = 'p', mods = 'SUPER', action = wezterm.action{SendString = '\x1bp'} },
        -- leave CMD + Q for close app
        -- { key = 'q', mods = 'SUPER', action = wezterm.action{SendString = '\x1bq'} },
        { key = 'r', mods = 'SUPER', action = wezterm.action{SendString = '\x1br'} },
        { key = 's', mods = 'SUPER', action = wezterm.action{SendString = '\x1bs'} },
        { key = 't', mods = 'SUPER', action = wezterm.action{SendString = '\x1bt'} },
        { key = 'u', mods = 'SUPER', action = wezterm.action{SendString = '\x1bu'} },
        -- leave CMD + V for paste
        -- { key = 'v', mods = 'SUPER', action = wezterm.action{SendString = '\x1bv'} },
        -- leave CMD + W for close tab
        -- { key = 'w', mods = 'SUPER', action = wezterm.action{SendString = '\x1bw'} },
        { key = 'x', mods = 'SUPER', action = wezterm.action{SendString = '\x1bx'} },
        { key = 'y', mods = 'SUPER', action = wezterm.action{SendString = '\x1by'} },
        { key = 'z', mods = 'SUPER', action = wezterm.action{SendString = '\x1bz'} },
    },
}
