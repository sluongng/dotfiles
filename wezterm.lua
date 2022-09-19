local wezterm = require 'wezterm'
local act = wezterm.action

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

local original_copy_mode = {
    {
      key = 'Tab',
      mods = 'NONE',
      action = act.CopyMode 'MoveForwardWord',
    },
    {
      key = 'Tab',
      mods = 'SHIFT',
      action = act.CopyMode 'MoveBackwardWord',
    },
    {
      key = 'Enter',
      mods = 'NONE',
      action = act.CopyMode 'MoveToStartOfNextLine',
    },
    { key = 'Escape', mods = 'NONE', action = act.CopyMode 'Close' },
    {
      key = 'Space',
      mods = 'NONE',
      action = act.CopyMode { SetSelectionMode = 'Cell' },
    },
    {
      key = '$',
      mods = 'NONE',
      action = act.CopyMode 'MoveToEndOfLineContent',
    },
    {
      key = '$',
      mods = 'SHIFT',
      action = act.CopyMode 'MoveToEndOfLineContent',
    },
    {
      key = '0',
      mods = 'NONE',
      action = act.CopyMode 'MoveToStartOfLine',
    },
    {
      key = 'G',
      mods = 'NONE',
      action = act.CopyMode 'MoveToScrollbackBottom',
    },
    {
      key = 'G',
      mods = 'SHIFT',
      action = act.CopyMode 'MoveToScrollbackBottom',
    },
    {
      key = 'H',
      mods = 'NONE',
      action = act.CopyMode 'MoveToViewportTop',
    },
    {
      key = 'H',
      mods = 'SHIFT',
      action = act.CopyMode 'MoveToViewportTop',
    },
    {
      key = 'L',
      mods = 'NONE',
      action = act.CopyMode 'MoveToViewportBottom',
    },
    {
      key = 'L',
      mods = 'SHIFT',
      action = act.CopyMode 'MoveToViewportBottom',
    },
    {
      key = 'M',
      mods = 'NONE',
      action = act.CopyMode 'MoveToViewportMiddle',
    },
    {
      key = 'M',
      mods = 'SHIFT',
      action = act.CopyMode 'MoveToViewportMiddle',
    },
    {
      key = 'O',
      mods = 'NONE',
      action = act.CopyMode 'MoveToSelectionOtherEndHoriz',
    },
    {
      key = 'O',
      mods = 'SHIFT',
      action = act.CopyMode 'MoveToSelectionOtherEndHoriz',
    },
    {
      key = 'V',
      mods = 'NONE',
      action = act.CopyMode { SetSelectionMode = 'Line' },
    },
    {
      key = 'V',
      mods = 'SHIFT',
      action = act.CopyMode { SetSelectionMode = 'Line' },
    },
    {
      key = '^',
      mods = 'NONE',
      action = act.CopyMode 'MoveToStartOfLineContent',
    },
    {
      key = '^',
      mods = 'SHIFT',
      action = act.CopyMode 'MoveToStartOfLineContent',
    },
    { key = 'b', mods = 'NONE', action = act.CopyMode 'MoveBackwardWord' },
    { key = 'b', mods = 'ALT', action = act.CopyMode 'MoveBackwardWord' },
    { key = 'b', mods = 'CTRL', action = act.CopyMode 'PageUp' },
    { key = 'c', mods = 'CTRL', action = act.CopyMode 'Close' },
    { key = 'f', mods = 'ALT', action = act.CopyMode 'MoveForwardWord' },
    { key = 'f', mods = 'CTRL', action = act.CopyMode 'PageDown' },
    {
      key = 'g',
      mods = 'NONE',
      action = act.CopyMode 'MoveToScrollbackTop',
    },
    { key = 'g', mods = 'CTRL', action = act.CopyMode 'Close' },
    { key = 'h', mods = 'NONE', action = act.CopyMode 'MoveLeft' },
    { key = 'j', mods = 'NONE', action = act.CopyMode 'MoveDown' },
    { key = 'k', mods = 'NONE', action = act.CopyMode 'MoveUp' },
    { key = 'l', mods = 'NONE', action = act.CopyMode 'MoveRight' },
    {
      key = 'm',
      mods = 'ALT',
      action = act.CopyMode 'MoveToStartOfLineContent',
    },
    {
      key = 'o',
      mods = 'NONE',
      action = act.CopyMode 'MoveToSelectionOtherEnd',
    },
    { key = 'q', mods = 'NONE', action = act.CopyMode 'Close' },
    {
      key = 'v',
      mods = 'NONE',
      action = act.CopyMode { SetSelectionMode = 'Cell' },
    },
    {
      key = 'v',
      mods = 'CTRL',
      action = act.CopyMode { SetSelectionMode = 'Block' },
    },
    { key = 'w', mods = 'NONE', action = act.CopyMode 'MoveForwardWord' },
    {
      key = 'y',
      mods = 'NONE',
      action = act.Multiple {
        { CopyTo = 'ClipboardAndPrimarySelection' },
        { CopyMode = 'Close' },
      },
    },
    { key = 'PageUp', mods = 'NONE', action = act.CopyMode 'PageUp' },
    { key = 'PageDown', mods = 'NONE', action = act.CopyMode 'PageDown' },
    { key = 'u', mods = 'CTRL', action = act.CopyMode 'PageUp' },
    { key = 'd', mods = 'CTRL', action = act.CopyMode 'PageDown' },
    { key = 'LeftArrow', mods = 'NONE', action = act.CopyMode 'MoveLeft' },
    {
      key = 'LeftArrow',
      mods = 'ALT',
      action = act.CopyMode 'MoveBackwardWord',
    },
    {
      key = 'RightArrow',
      mods = 'NONE',
      action = act.CopyMode 'MoveRight',
    },
    {
      key = 'RightArrow',
      mods = 'ALT',
      action = act.CopyMode 'MoveForwardWord',
    },
    { key = 'UpArrow', mods = 'NONE', action = act.CopyMode 'MoveUp' },
    { key = 'DownArrow', mods = 'NONE', action = act.CopyMode 'MoveDown' },
}

-- My customization
custom_copy_mode = original_copy_mode
table.insert(
    custom_copy_mode,
    { key = 'u', mods = 'CTRL', action = act.CopyMode 'PageUp' }
)
table.insert(
    custom_copy_mode,
    { key = 'd', mods = 'CTRL', action = act.CopyMode 'PageDown' }
)

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

    scrollback_lines = 9001,

    -- Tab bar style
    tab_bar_at_bottom = true,
    hide_tab_bar_if_only_one_tab = true,

    leader = { 
        -- key = 'b',
        key = 'a',
        mods = 'CTRL',
        timeout_milliseconds = 1000,
    },

    key_tables = {
        -- We cannot override the original copy_mode table
        -- so copy paste from default setting and then add our own
        copy_mode = custom_copy_mode,
    },

    keys = {
        -- Send 'CTRL-b' to the terminal when pressing CTRL-b, CTRL-b
        -- { key = 'b', mods = 'LEADER|CTRL',     action = act.SendString '\x02' },
        { key = 'a', mods = 'LEADER|CTRL',     action = act.SendString '\x01' },
        { key = 'f', mods = 'CMD|CTRL', action = act.ToggleFullScreen },

        {
            key="e", mods="CTRL|SHIFT",
            action=act{QuickSelectArgs={
                patterns={
                   "https?://\\S+"
                },
                action = wezterm.action_callback(
                    function(window, pane)
                       local url = window:get_selection_text_for_pane(pane)
                       wezterm.log_info("opening: " .. url)
                       wezterm.open_with(url)
                    end
                )
            }}
        },

        -- **Copy Mode**
        { key = '[', mods = 'LEADER', action = act.ActivateCopyMode },


        -- **Screen management**
        { key = 'c', mods = 'LEADER', action = act.SpawnTab 'CurrentPaneDomain' },
        { key = 'p', mods = 'LEADER', action = act.ActivateTabRelative(-1) },
        { key = 'n', mods = 'LEADER', action = act.ActivateTabRelative(2) },
        { key = 'o', mods = 'LEADER', action = act.ActivatePaneDirection 'Next' },
        { key = 'l', mods = 'LEADER', action = act.SplitHorizontal {domain = 'CurrentPaneDomain'} },
        { key = 'j', mods = 'LEADER', action = act.SplitVertical {domain = 'CurrentPaneDomain'} },

        -- Quick open http links using Ctrl + Shift + E
        {
            key="e", mods="CTRL|SHIFT",
            action=act{QuickSelectArgs={
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
        {key = 'w', mods = 'CMD', action = act.CloseCurrentPane { confirm = true } },

        -- **Editor/Shell navigations**
        { key = 'a', mods = 'SUPER', action = act{SendString = '\x1ba'} },
        { key = 'b', mods = 'SUPER', action = act{SendString = '\x1bb'} },
        -- leave CMD + C for copy
        -- { key = 'c', mods = 'SUPER', action = act{SendString = '\x1bc'} },
        { key = 'd', mods = 'SUPER', action = act{SendString = '\x1bd'} },
        { key = 'e', mods = 'SUPER', action = act{SendString = '\x1be'} },
        -- { key = 'f', mods = 'SUPER', action = act{SendString = '\x1bf'} },
        { key = 'g', mods = 'SUPER', action = act{SendString = '\x1bg'} },
        { key = 'h', mods = 'SUPER', action = act{SendString = '\x1bh'} },
        { key = 'i', mods = 'SUPER', action = act{SendString = '\x1bi'} },
        { key = 'j', mods = 'SUPER', action = act{SendString = '\x1bj'} },
        { key = 'k', mods = 'SUPER', action = act{SendString = '\x1bk'} },
        { key = 'l', mods = 'SUPER', action = act{SendString = '\x1bl'} },
        { key = 'm', mods = 'SUPER', action = act{SendString = '\x1bm'} },
        { key = 'n', mods = 'SUPER', action = act{SendString = '\x1bn'} },
        { key = 'o', mods = 'SUPER', action = act{SendString = '\x1bo'} },
        { key = 'p', mods = 'SUPER', action = act{SendString = '\x1bp'} },
        -- leave CMD + Q for close app
        -- { key = 'q', mods = 'SUPER', action = act{SendString = '\x1bq'} },
        { key = 'r', mods = 'SUPER', action = act{SendString = '\x1br'} },
        { key = 's', mods = 'SUPER', action = act{SendString = '\x1bs'} },
        { key = 't', mods = 'SUPER', action = act{SendString = '\x1bt'} },
        { key = 'u', mods = 'SUPER', action = act{SendString = '\x1bu'} },
        -- leave CMD + V for paste
        -- { key = 'v', mods = 'SUPER', action = act{SendString = '\x1bv'} },
        -- leave CMD + W for close tab
        -- { key = 'w', mods = 'SUPER', action = act{SendString = '\x1bw'} },
        { key = 'x', mods = 'SUPER', action = act{SendString = '\x1bx'} },
        { key = 'y', mods = 'SUPER', action = act{SendString = '\x1by'} },
        { key = 'z', mods = 'SUPER', action = act{SendString = '\x1bz'} },
    },
}
