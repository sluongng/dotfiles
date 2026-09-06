#!/usr/bin/env python3
"""Exercise role deployment without running the installer or touching live state."""

from pathlib import Path
import subprocess
import tempfile
import unittest


INSTALLER = Path(__file__).with_name("install-codex.sh")


class RoleDeploymentTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "tracked" / "reviewer.toml"
        self.source.parent.mkdir()
        self.source.write_text('name = "reviewer"\n')
        self.target_root = self.root / "runtime"
        self.target = self.target_root / "agents" / self.source.name
        self.target.parent.mkdir(parents=True)
        self.backup = self.target_root / "backups" / "test"

    def deploy(self, *, check=True):
        return subprocess.run(
            [
                "bash", "-c",
                'source "$1"; TARGET_DIR="$2"; BACKUP_DIR="$3"; ensure_regular_file "$4" "$5"',
                "test-role-deployment", str(INSTALLER), str(self.target_root),
                str(self.backup), str(self.source), str(self.target),
            ],
            check=check, text=True, capture_output=True,
        )

    def test_replaces_symlink_without_writing_source_and_is_idempotent(self):
        self.target.symlink_to(self.source)
        source_stat = self.source.stat()
        self.deploy()
        self.assertFalse(self.target.is_symlink())
        self.assertEqual(self.target.read_bytes(), self.source.read_bytes())
        self.assertEqual(self.source.stat(), source_stat)
        saved_link = self.backup / "agents" / self.source.name
        self.assertTrue(saved_link.is_symlink())
        self.assertEqual(saved_link.readlink(), self.source)
        deployed_stat = self.target.stat()
        self.deploy()
        self.assertEqual(self.target.stat(), deployed_stat)
        self.assertEqual(list(saved_link.parent.iterdir()), [saved_link])

    def test_updates_regular_file_and_preserves_previous_versions(self):
        self.target.write_text("first local version\n")
        self.deploy()
        saved = self.backup / "agents" / self.source.name
        self.assertEqual(saved.read_text(), "first local version\n")
        self.source.write_text('name = "reviewer"\nmodel = "new-model"\n')
        self.deploy()
        self.assertEqual(saved.read_text(), "first local version\n")
        self.assertEqual(saved.with_name(saved.name + ".1").read_text(), 'name = "reviewer"\n')
        self.assertEqual(self.target.read_bytes(), self.source.read_bytes())
        self.assertEqual(list(self.target.parent.glob(".reviewer.toml.*")), [])

    def test_missing_source_keeps_existing_destination(self):
        self.target.write_text("keep this\n")
        self.source.unlink()
        result = self.deploy(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_text(), "keep this\n")
        self.assertEqual(list(self.target.parent.glob(".reviewer.toml.*")), [])
        self.assertFalse(self.backup.exists())

    def test_rejects_symlink_directory_without_touching_source(self):
        self.target.parent.rmdir()
        self.target.parent.symlink_to(self.source.parent, target_is_directory=True)
        source_stat = self.source.stat()
        result = self.deploy(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink directory", result.stderr)
        self.assertEqual(self.source.stat(), source_stat)
        self.assertEqual(list(self.source.parent.iterdir()), [self.source])


if __name__ == "__main__":
    unittest.main()
