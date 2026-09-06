---
name: "screenshot"
description: "Capture desktop, app, window, or region screenshots when requested or when an OS capture is needed and no suitable tool-specific capture is available."
---


# Screenshot Capture

Follow these save-location rules every time:

1) If the user specifies a path, save there.
2) If the user asks for a screenshot without a path, save to the OS default screenshot location.
3) If Codex needs a screenshot for its own inspection, save to the temp directory.

## Tool priority

- Prefer tool-specific screenshot capabilities when available (for example: a Figma MCP/skill for Figma files, or the built-in Browser/Chrome tools for web pages and browser apps).
- Use this skill when explicitly asked, for whole-system desktop captures, or when a tool-specific capture cannot get what you need.
- Otherwise, treat this skill as the default for desktop apps without a better-integrated capture tool.

## Capture on the current platform

Read only the reference needed for this host:

- **macOS:** [references/macos.md](references/macos.md) for Screen Recording
  permission and OS fallbacks, then
  [references/python-capture.md](references/python-capture.md) for helper flags.
- **Linux X11:** [references/python-capture.md](references/python-capture.md).
  The helper uses scrot, gnome-screenshot, or ImageMagick import.
- **Linux Wayland/Hyprland:** prefer the installed `linux-computer-use` screenshot
  capability. The bundled Python helper has no native Wayland backend; use an
  available compositor capture tool such as `grim` when needed.
- **Windows:** [references/windows.md](references/windows.md).

The helper prints one path per capture. For visual inspection, view the returned
images; when multiple windows or displays match, inspect each relevant capture.
Always report saved paths to the user.

## Recovery

If capture fails, inspect the specific platform/tool error and use its documented
fallback. On macOS, run the permission preflight before retrying capture; list
matching windows if an app/window selector returned no matches. Request elevated
permissions only when the active tool policy supports that path and the error
requires it. Preserve the requested save location, or report the failure if it
cannot be written.
