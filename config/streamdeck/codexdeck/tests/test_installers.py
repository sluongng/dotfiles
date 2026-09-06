"""Installer failure paths with private files and fake external commands."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


PLUGIN = Path(__file__).parents[1]


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="codexdeck-install-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.commands = self.root / "bin"
        self.commands.mkdir()
        self.log = self.root / "commands.log"
        self.env = {
            **os.environ,
            "HOME": str(self.root / "home"),
            "PATH": str(self.commands) + os.pathsep + os.environ["PATH"],
            "TEST_LOG": str(self.log),
            "STREAMCONTROLLER_DATA_DIR": str(self.root / "data"),
            "XDG_CONFIG_HOME": str(self.root / "config"),
        }
        self.command("systemctl", 'printf "%s\\n" "$*" >> "$TEST_LOG"\n')

    def command(self, name, body):
        destination = self.commands / name
        destination.write_text("#!/bin/sh\nset -eu\n" + body)
        destination.chmod(0o755)

    def run_installer(self, name):
        return subprocess.run(
            ["bash", str(PLUGIN / name)], env=self.env,
            capture_output=True, text=True, timeout=10,
        )

    def page(self):
        page = self.root / "data/pages/first.json"
        page.parent.mkdir(parents=True)
        page.write_text("original page")
        return page

    def test_page_backup_failure_restores_service_and_preserves_page(self):
        page = self.page()
        self.command("cp", "exit 12\n")
        result = self.run_installer("install-page.sh")
        self.assertEqual(result.returncode, 12, result.stderr)
        self.assertEqual(page.read_text(), "original page")
        self.assertEqual(
            self.log.read_text().splitlines(),
            [
                "--user is-active --quiet app-StreamController@autostart.service",
                "--user stop app-StreamController@autostart.service",
                "--user start app-StreamController@autostart.service",
            ],
        )
        self.assertEqual(list(page.parent.glob(".first.*")), [])

    def test_page_staging_failure_does_not_stop_service(self):
        page = self.page()
        self.command("install", "exit 13\n")
        result = self.run_installer("install-page.sh")
        self.assertEqual(result.returncode, 13, result.stderr)
        self.assertEqual(page.read_text(), "original page")
        self.assertFalse(self.log.exists())
        self.assertEqual(list(page.parent.glob(".first.*")), [])

    def test_page_install_preserves_backup_and_restores_service(self):
        page = self.page()
        result = self.run_installer("install-page.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(page.read_bytes(), (PLUGIN / "page.json").read_bytes())
        backups = list((page.parent / "backups").glob("first-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "original page")
        self.assertTrue(self.log.read_text().endswith("--user start app-StreamController@autostart.service\n"))

    def test_dictation_config_conflict_prevents_download_and_binary_change(self):
        target = self.root / "config/voxtype/config.toml"
        target.parent.mkdir(parents=True)
        target.write_text("existing config")
        binary = self.root / "home/.local/bin/voxtype"
        binary.parent.mkdir(parents=True)
        binary.write_text("existing binary")
        self.command("uname", "echo x86_64\n")
        self.command("grep", "exit 0\n")
        self.command("curl", 'echo unexpected-download >> "$TEST_LOG"\nexit 90\n')
        result = self.run_installer("install-dictation.sh")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Refusing to replace existing path", result.stderr)
        self.assertEqual(target.read_text(), "existing config")
        self.assertEqual(binary.read_text(), "existing binary")
        self.assertFalse(self.log.exists())
