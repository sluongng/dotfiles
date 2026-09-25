#!/usr/bin/env python3

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "automation/codex/render-config.py"
SHARED = ROOT / "config/codex/config.toml"
INSTALLER = ROOT / "automation/codex/install-codex.sh"


class RenderConfigTest(unittest.TestCase):
    def test_installer_probes_context_support_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "codex"
            binary.write_text('''#!/bin/sh
case "$(cat "$CODEX_HOME/config.toml")" in
  *context_management*) [ "$CODEX_TEST_CONTEXT_SUPPORT" = true ] ;;
  *) exit 0 ;;
esac
''')
            binary.chmod(0o755)
            for supported, override, expected in (
                ("false", "", ["true", "false"]),
                ("true", "", ["true", "true"]),
                ("true", "false", ["true", "false"]),
            ):
                with self.subTest(supported=supported, override=override):
                    env = os.environ.copy()
                    env["PATH"] = str(binary.parent) + os.pathsep + env["PATH"]
                    env["CODEX_TEST_CONTEXT_SUPPORT"] = supported
                    env["CODEX_NESTED_FEATURE_TABLES"] = ""
                    env["CODEX_CONTEXT_MANAGEMENT_TABLE"] = override
                    result = subprocess.run(
                        ["bash", "-c", 'source "$1"; detect_nested_feature_tables; detect_context_management_table',
                         "test-config-probes", str(INSTALLER)],
                        env=env, check=True, capture_output=True, text=True,
                    )
                    self.assertEqual(result.stdout.splitlines(), expected)

    def render(
        self,
        *,
        platform: str,
        nested_features: bool,
        context_management: bool = True,
        local_text: str = "",
        runtime_text: str = "",
        target_text: str | None = None,
        render_count: int = 1,
        python_executable: str = sys.executable,
    ) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            local = root / "config.local.toml"
            projects = root / "projects.local.toml"
            runtime = root / "runtime.local.toml"
            target = root / "config.toml"
            local.write_text(local_text)
            projects.write_text("")
            runtime.write_text(runtime_text)
            if target_text is not None:
                target.write_text(target_text)
            command = [
                python_executable,
                str(RENDERER),
                "--shared",
                str(SHARED),
                "--local",
                str(local),
                "--projects",
                str(projects),
                "--runtime",
                str(runtime),
                "--target",
                str(target),
                "--platform",
                platform,
                "--nested-feature-tables",
                str(nested_features).lower(),
                "--context-management-table",
                str(context_management).lower(),
                "--marketplace-name",
                "sluongng-dotfiles",
                "--marketplace-source",
                str(ROOT / "config/codex"),
            ]
            for _ in range(render_count):
                subprocess.run(command, check=True, capture_output=True, text=True)
            with target.open("rb") as rendered:
                return tomllib.load(rendered)

    def test_preserves_ui_preferences_across_rerenders_without_freezing_shared_settings(self) -> None:
        config = self.render(
            platform="Linux",
            nested_features=True,
            render_count=2,
            target_text='''
[tui]
session_picker_view = "comfortable"
screen_reader_detection_done = false
fullscreen_transcript = true

[desktop]
open_fullscreen = true

[plugins."github@openai-curated"]
enabled = true
''',
            local_text='''
[tui.model_availability_nux]
"gpt-6-sol" = true
''',
        )
        self.assertEqual(config["tui"]["session_picker_view"], "comfortable")
        self.assertIs(config["tui"]["screen_reader_detection_done"], False)
        self.assertFalse(config["tui"]["fullscreen_transcript"])
        self.assertTrue(config["tui"]["model_availability_nux"]["gpt-6-sol"])
        self.assertTrue(config["desktop"]["open_fullscreen"])
        self.assertNotIn("github@openai-curated", config["plugins"])
        self.assertTrue(config["plugins"]["github@openai-curated-remote"]["enabled"])

    def test_restores_ui_preferences_from_runtime_overlay_on_first_render(self) -> None:
        config = self.render(
            platform="Linux",
            nested_features=True,
            runtime_text='''
[tui]
session_picker_view = "comfortable"
screen_reader_detection_done = true
''',
        )
        self.assertEqual(config["tui"]["session_picker_view"], "comfortable")
        self.assertTrue(config["tui"]["screen_reader_detection_done"])

    def test_preserves_app_managed_runtime_tables(self) -> None:
        config = self.render(
            platform="Linux",
            nested_features=True,
            runtime_text='''
[marketplaces.openai-bundled]
source_type = "bundled"

[plugins."browser@openai-bundled"]
enabled = true

[mcp_servers.node_repl]
command = "/runtime/node"

[shell_environment_policy.set]
NODE_REPL_TRUSTED_CODE_PATHS = "/runtime/node"

[desktop]
open_fullscreen = true
''',
        )

        self.assertEqual(
            config["marketplaces"]["openai-bundled"]["source_type"],
            "bundled",
        )
        self.assertTrue(config["plugins"]["browser@openai-bundled"]["enabled"])
        self.assertEqual(config["mcp_servers"]["node_repl"]["command"], "/runtime/node")
        self.assertEqual(
            config["shell_environment_policy"]["set"]["NODE_REPL_TRUSTED_CODE_PATHS"],
            "/runtime/node",
        )
        self.assertTrue(config["desktop"]["open_fullscreen"])

    def test_sync_removes_stale_runtime_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            local = root / "config.local.toml"
            projects = root / "projects.local.toml"
            runtime = root / "runtime.local.toml"
            target = root / "config.toml"
            local.write_text("")
            projects.write_text("")
            runtime.write_text('[desktop]\nopen_fullscreen = true\n')
            target.write_text('model = "gpt-5.6-sol"\n')

            subprocess.run(
                [
                    sys.executable,
                    str(RENDERER),
                    "--shared",
                    str(SHARED),
                    "--local",
                    str(local),
                    "--projects",
                    str(projects),
                    "--runtime",
                    str(runtime),
                    "--target",
                    str(target),
                    "--platform",
                    "Linux",
                    "--nested-feature-tables",
                    "true",
                    "--marketplace-name",
                    "sluongng-dotfiles",
                    "--marketplace-source",
                    str(ROOT / "config/codex"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertFalse(runtime.exists())

    def test_sync_preserves_nested_desktop_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            local = root / "config.local.toml"
            projects = root / "projects.local.toml"
            runtime = root / "runtime.local.toml"
            target = root / "config.toml"
            local.write_text("")
            projects.write_text("")
            target.write_text(
                '''
[desktop]
appearanceLightCodeThemeId = "codex"

[desktop.appearanceLightChromeTheme]
accent = "#0169cc"

[desktop.appearanceLightChromeTheme.semanticColors]
diffAdded = "#00a240"
'''
            )

            subprocess.run(
                [
                    sys.executable,
                    str(RENDERER),
                    "--shared",
                    str(SHARED),
                    "--local",
                    str(local),
                    "--projects",
                    str(projects),
                    "--runtime",
                    str(runtime),
                    "--target",
                    str(target),
                    "--platform",
                    "Linux",
                    "--nested-feature-tables",
                    "true",
                    "--marketplace-name",
                    "sluongng-dotfiles",
                    "--marketplace-source",
                    str(ROOT / "config/codex"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            with runtime.open("rb") as runtime_file:
                runtime_config = tomllib.load(runtime_file)
            self.assertEqual(
                runtime_config["desktop"]["appearanceLightChromeTheme"],
                {"accent": "#0169cc", "semanticColors": {"diffAdded": "#00a240"}},
            )

            with target.open("rb") as rendered_file:
                rendered_config = tomllib.load(rendered_file)
            self.assertEqual(
                rendered_config["desktop"]["appearanceLightChromeTheme"],
                runtime_config["desktop"]["appearanceLightChromeTheme"],
            )

    def test_sync_preserves_nested_hook_state_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            local = root / "config.local.toml"
            projects = root / "projects.local.toml"
            runtime = root / "runtime.local.toml"
            target = root / "config.toml"
            local.write_text("")
            projects.write_text("")
            hook_key = "/home/example/.codex/hooks.json:session_start:0:0"
            target.write_text(
                f'''
[hooks.state]

[hooks.state."{hook_key}"]
trusted_hash = "sha256:test"
'''
            )

            subprocess.run(
                [
                    sys.executable,
                    str(RENDERER),
                    "--shared",
                    str(SHARED),
                    "--local",
                    str(local),
                    "--projects",
                    str(projects),
                    "--runtime",
                    str(runtime),
                    "--target",
                    str(target),
                    "--platform",
                    "Linux",
                    "--nested-feature-tables",
                    "true",
                    "--marketplace-name",
                    "sluongng-dotfiles",
                    "--marketplace-source",
                    str(ROOT / "config/codex"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            expected_hooks = {
                "state": {hook_key: {"trusted_hash": "sha256:test"}}
            }
            with runtime.open("rb") as runtime_file:
                runtime_config = tomllib.load(runtime_file)
            self.assertEqual(runtime_config["hooks"], expected_hooks)

            with target.open("rb") as rendered_file:
                rendered_config = tomllib.load(rendered_file)
            self.assertEqual(rendered_config["hooks"], expected_hooks)

    def test_legacy_macos_uses_cross_runtime_safe_settings(self) -> None:
        config = self.render(
            platform="Darwin",
            nested_features=False,
            context_management=False,
            local_text='''
[plugins."buildbuddy@sluongng-dotfiles"]
enabled = true
''',
        )

        self.assertFalse(config["features"]["shell_zsh_fork"])
        self.assertNotIn("unified_exec_zsh_fork", config["features"])
        self.assertTrue(config["features"]["multi_agent_v2"])
        self.assertTrue(config["features"]["current_time_reminder"])
        self.assertNotIn("agents", config)
        self.assertNotIn("context_management", config["features"])
        self.assertFalse(
            config["plugins"]["chatgpt-threads@sluongng-dotfiles"]["enabled"]
        )

    def test_modern_linux_keeps_nested_features(self) -> None:
        config = self.render(
            platform="Linux", nested_features=True
        )

        self.assertFalse(config["features"]["shell_zsh_fork"])
        self.assertTrue(config["features"]["multi_agent_v2"]["enabled"])
        self.assertTrue(config["features"]["current_time_reminder"]["enabled"])
        self.assertTrue(config["features"]["context_management"]["experimental_mode"])
        self.assertEqual(config["agents"]["max_depth"], 2)
        self.assertTrue(
            config["plugins"]["chatgpt-threads@sluongng-dotfiles"]["enabled"]
        )
        self.assertEqual(
            config["marketplaces"]["sluongng-dotfiles"]["source_type"],
            "local",
        )

    def test_context_management_support_is_independent_of_other_nested_features(self) -> None:
        for platform in ("Darwin", "Linux"):
            with self.subTest(platform=platform):
                config = self.render(
                    platform=platform, nested_features=True, context_management=False
                )
                self.assertNotIn("context_management", config["features"])
                self.assertTrue(config["features"]["multi_agent_v2"]["enabled"])
                self.assertTrue(config["features"]["current_time_reminder"]["enabled"])

    @unittest.skipUnless(Path("/usr/bin/python3").is_file(), "no system Python")
    def test_stock_macos_python_can_render_without_tomllib(self) -> None:
        config = self.render(
            platform="Darwin",
            nested_features=False,
            python_executable="/usr/bin/python3",
        )

        self.assertFalse(config["features"]["shell_zsh_fork"])
        self.assertTrue(config["features"]["current_time_reminder"])

    @unittest.skipUnless(Path("/usr/bin/python3").is_file(), "no system Python")
    def test_stock_macos_python_rejects_invalid_local_toml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            local = root / "config.local.toml"
            projects = root / "projects.local.toml"
            target = root / "config.toml"
            local.write_text('[plugins."broken"]\nenabled = definitely-not-toml\n')
            projects.write_text("")
            result = subprocess.run(
                [
                    "/usr/bin/python3",
                    str(RENDERER),
                    "--shared",
                    str(SHARED),
                    "--local",
                    str(local),
                    "--projects",
                    str(projects),
                    "--target",
                    str(target),
                    "--platform",
                    "Darwin",
                    "--nested-feature-tables",
                    "false",
                    "--marketplace-name",
                    "sluongng-dotfiles",
                    "--marketplace-source",
                    str(ROOT / "config/codex"),
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid TOML", result.stderr)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
