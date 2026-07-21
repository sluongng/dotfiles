hl.config({
    animations = {
        enabled = true,
    },
})

hl.curve("overshot", {
    type = "bezier",
    points = { { 0.13, 0.99 }, { 0.29, 1.1 } },
})

hl.animation({ leaf = "windowsIn", enabled = true, speed = 4, bezier = "overshot", style = "slide" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 5, bezier = "default", style = "popin 80%" })
hl.animation({ leaf = "border", enabled = true, speed = 5, bezier = "default" })
hl.animation({ leaf = "windowsMove", enabled = false })
hl.animation({ leaf = "workspacesIn", enabled = false })
hl.animation({ leaf = "workspacesOut", enabled = false })
