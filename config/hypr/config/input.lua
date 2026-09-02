hl.config({
    input = {
        follow_mouse = 2,
        float_switch_override_focus = 2,
        repeat_rate = 40,
        repeat_delay = 200,
        kb_options = "ctrl:nocaps",
    },
})

-- Keep the Nape Pro sensor at 4000 DPI while compensating for its much higher
-- resolution and matching the MX Ergo's perceived pointer speed.
hl.device({
    name = "keychron-keychron-nape-pro-mouse",
    accel_profile = "custom 1 0 0.300",
})
hl.device({
    name = "keychron-nape-pro-mouse",
    accel_profile = "custom 1 0 0.300",
})
