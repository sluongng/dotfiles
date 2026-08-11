#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "automation/codex/render-config.py"
SHARED = ROOT / "config/codex/config.toml"


class RenderConfigTest(unittest.TestCase):
    def render(
        self,
        *,
        platform: str,
        nested_features: bool,
        local_text: str = "",
        runtime_text: str = "",
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
            subprocess.run(
                [
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
                    "--marketplace-name",
                    "sluongng-dotfiles",
                    "--marketplace-source",
                    str(ROOT / "config/codex"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            with target.open("rb") as rendered:
                return tomllib.load(rendered)

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

    def test_legacy_macos_uses_cross_runtime_safe_settings(self) -> None:
        config = self.render(
            platform="Darwin",
            nested_features=False,
            local_text='''
[plugins."buildbuddy@sluongng-dotfiles"]
enabled = true
''',
        )

        self.assertFalse(config["features"]["shell_zsh_fork"])
        self.assertFalse(config["features"]["unified_exec_zsh_fork"])
        self.assertTrue(config["features"]["multi_agent_v2"])
        self.assertTrue(config["features"]["current_time_reminder"])
        self.assertNotIn("agents", config)
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
        self.assertEqual(config["agents"]["max_depth"], 2)
        self.assertTrue(
            config["plugins"]["chatgpt-threads@sluongng-dotfiles"]["enabled"]
        )
        self.assertEqual(
            config["marketplaces"]["sluongng-dotfiles"]["source_type"],
            "local",
        )

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
