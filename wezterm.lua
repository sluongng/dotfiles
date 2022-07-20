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

        { key= "a", mods= "SUPER", action=wezterm.action{SendString="\x1ba"                       }},
        { key= "b", mods= "SUPER", action=wezterm.action{SendString="\x1bb"                       }},
        -- { key= "c", mods= "SUPER", action=wezterm.action{SendString="\x1bc"                       }},
        { key= "d", mods= "SUPER", action=wezterm.action{SendString="\x1bd"                       }},
        { key= "e", mods= "SUPER", action=wezterm.action{SendString="\x1be"                       }},
        { key= "f", mods= "SUPER", action=wezterm.action{SendString="\x1bf"                       }},
        { key= "g", mods= "SUPER", action=wezterm.action{SendString="\x1bg"                       }},
        { key= "h", mods= "SUPER", action=wezterm.action{SendString="\x1bh"                       }},
        { key= "i", mods= "SUPER", action=wezterm.action{SendString="\x1bi"                       }},
        { key= "j", mods= "SUPER", action=wezterm.action{SendString="\x1bj"                       }},
        { key= "k", mods= "SUPER", action=wezterm.action{SendString="\x1bk"                       }},
        { key= "l", mods= "SUPER", action=wezterm.action{SendString="\x1bl"                       }},
        { key= "m", mods= "SUPER", action=wezterm.action{SendString="\x1bm"                       }},
        { key= "n", mods= "SUPER", action=wezterm.action{SendString="\x1bn"                       }},
        { key= "o", mods= "SUPER", action=wezterm.action{SendString="\x1bo"                       }},
        { key= "p", mods= "SUPER", action=wezterm.action{SendString="\x1bp"                       }},
        { key= "q", mods= "SUPER", action=wezterm.action{SendString="\x1bq"                       }},
        { key= "r", mods= "SUPER", action=wezterm.action{SendString="\x1br"                       }},
        { key= "s", mods= "SUPER", action=wezterm.action{SendString="\x1bs"                       }},
        { key= "t", mods= "SUPER", action=wezterm.action{SendString="\x1bt"                       }},
        { key= "u", mods= "SUPER", action=wezterm.action{SendString="\x1bu"                       }},
        -- { key= "v", mods= "SUPER", action=wezterm.action{SendString="\x1bv"                       }},
        { key= "w", mods= "SUPER", action=wezterm.action{SendString="\x1bw"                       }},
        { key= "x", mods= "SUPER", action=wezterm.action{SendString="\x1bx"                       }},
        { key= "y", mods= "SUPER", action=wezterm.action{SendString="\x1by"                       }},
        { key= "z", mods= "SUPER", action=wezterm.action{SendString="\x1bz"                       }},

    },
}
