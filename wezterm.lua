local wezterm = require 'wezterm'

return {
    font = wezterm.font {
        family = 'Hack Nerd Font',
    },
    font_size = 11.0,

    hide_tab_bar_if_only_one_tab = true,

    leader = { 
        key = 'b',
        mods = 'CTRL',
        timeout_milliseconds = 1000,
    },
    keys = {
        {
            key = 'l',
            mods = 'LEADER',
            action = wezterm.action.SplitHorizontal {domain='CurrentPaneDomain'},
        },
        -- Send "CTRL-b" to the terminal when pressing CTRL-b, CTRL-b
        {
          key = 'b',
          mods = 'CTRL',
          action = wezterm.action.SendString '\x02',
        },
    },
}
