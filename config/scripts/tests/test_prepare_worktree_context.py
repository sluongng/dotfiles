import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "prepare-worktree-context"
DOTFILES_ROOT = SCRIPT.parents[2]
INSTALLER = DOTFILES_ROOT / "automation" / "codex" / "install-codex.sh"


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class PrepareWorktreeContextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        temp_root = Path(self.temp_dir.name)
        self.primary = temp_root / "primary"
        self.worktree = temp_root / "worktree"

        run(["git", "init", "-b", "main", str(self.primary)])
        run(["git", "config", "user.name", "Codex Test"], cwd=self.primary)
        run(["git", "config", "user.email", "codex-test@example.com"], cwd=self.primary)
        (self.primary / ".gitignore").write_text("user.bazelrc\n")
        (self.primary / "tracked.txt").write_text("tracked\n")
        run(["git", "add", ".gitignore", "tracked.txt"], cwd=self.primary)
        run(["git", "commit", "-m", "initial"], cwd=self.primary)
        run(["git", "worktree", "add", "--detach", str(self.worktree), "HEAD"], cwd=self.primary)

    def invoke(
        self,
        mode: str,
        *,
        use_environment: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        command = [str(SCRIPT), mode]
        environment = os.environ.copy()
        if use_environment:
            environment["CODEX_SOURCE_TREE_PATH"] = str(self.primary)
            environment["CODEX_WORKTREE_PATH"] = str(self.worktree)
        else:
            command.extend(
                ["--primary", str(self.primary), "--worktree", str(self.worktree)]
            )
        return subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )

    def test_dry_run_and_apply_copy_known_local_context(self) -> None:
        source = self.primary / "user.bazelrc"
        source.write_text("build --config=remote\n")
        nested_agents = self.primary / "nested" / "AGENTS.md"
        nested_agents.parent.mkdir()
        nested_agents.write_text("local instructions\n")

        dry_run = self.invoke("--dry-run")

        self.assertEqual(dry_run.returncode, 0)
        self.assertIn("would-copy\tuser.bazelrc", dry_run.stdout)
        self.assertIn("would-copy\tnested/AGENTS.md", dry_run.stdout)
        self.assertFalse((self.worktree / "user.bazelrc").exists())

        applied = self.invoke("--apply")

        self.assertEqual(applied.returncode, 0)
        destination = self.worktree / "user.bazelrc"
        self.assertEqual(destination.read_text(), source.read_text())
        self.assertNotEqual(destination.stat().st_ino, source.stat().st_ino)
        self.assertEqual(
            (self.worktree / "nested" / "AGENTS.md").read_text(),
            nested_agents.read_text(),
        )

    def test_existing_destination_is_not_overwritten(self) -> None:
        (self.primary / "user.bazelrc").write_text("source\n")
        destination = self.worktree / "user.bazelrc"
        destination.write_text("destination\n")

        result = self.invoke("--apply")

        self.assertEqual(result.returncode, 0)
        self.assertIn("skipped-existing-destination\tuser.bazelrc", result.stdout)
        self.assertEqual(destination.read_text(), "destination\n")

    def test_uses_codex_worktree_environment(self) -> None:
        (self.primary / ".bazelrc.user").write_text("build --announce_rc\n")

        result = self.invoke("--apply", use_environment=True)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            (self.worktree / ".bazelrc.user").read_text(),
            "build --announce_rc\n",
        )

    def test_copies_only_ignored_regular_files_matched_by_worktreeinclude(
        self,
    ) -> None:
        (self.primary / ".gitignore").write_text(
            "user.bazelrc\nlocal/\nvisible.local\n"
        )
        (self.primary / ".worktreeinclude").write_text(
            "local/**\n!local/skipped.txt\nvisible.local\n"
        )
        local = self.primary / "local"
        local.mkdir()
        included = local / "included.txt"
        included.write_text("included\n")
        (local / "skipped.txt").write_text("skipped\n")
        (self.primary / "visible.local").write_text("visible but ignored\n")
        (self.primary / "not-ignored.local").write_text("not ignored\n")

        result = self.invoke("--apply")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.worktree / "local" / "included.txt").read_text(),
            included.read_text(),
        )
        self.assertEqual(
            (self.worktree / "visible.local").read_text(),
            "visible but ignored\n",
        )
        self.assertFalse((self.worktree / "local" / "skipped.txt").exists())
        self.assertFalse((self.worktree / "not-ignored.local").exists())
        self.assertIn(
            "copied\tlocal/included.txt\tmatched .worktreeinclude",
            result.stdout,
        )

    def test_skips_source_symlinks_matched_by_worktreeinclude(self) -> None:
        (self.primary / ".gitignore").write_text("local-link\n")
        (self.primary / ".worktreeinclude").write_text("local-link\n")
        (self.primary / "secret.txt").write_text("secret\n")
        (self.primary / "local-link").symlink_to("secret.txt")

        result = self.invoke("--apply")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skipped-source-symlink\tlocal-link", result.stdout)
        self.assertFalse((self.worktree / "local-link").exists())

    def test_does_not_traverse_destination_symlink_parent(self) -> None:
        (self.primary / ".gitignore").write_text("local/\n")
        (self.primary / ".worktreeinclude").write_text("local/**\n")
        local = self.primary / "local"
        local.mkdir()
        (local / "settings.txt").write_text("settings\n")
        outside = Path(self.temp_dir.name) / "outside"
        outside.mkdir()
        (self.worktree / "local").symlink_to(outside, target_is_directory=True)

        result = self.invoke("--apply")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "skipped-destination-symlink-parent\tlocal/settings.txt",
            result.stdout,
        )
        self.assertFalse((outside / "settings.txt").exists())


class InstallPrepareWorktreeContextTest(unittest.TestCase):
    def test_installer_backs_up_existing_target_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            codex_home = temp_root / "codex-home"
            bin_home = temp_root / "bin"
            bin_home.mkdir()
            target = bin_home / "prepare-worktree-context"
            target.write_text("old executable\n")
            environment = os.environ.copy()
            environment["CODEX_HOME"] = str(codex_home)
            environment["CODEX_BIN_HOME"] = str(bin_home)

            first = subprocess.run(
                [str(INSTALLER)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), SCRIPT.resolve())
            backups = list(
                codex_home.glob(
                    "backups/install-codex-*/user-bin/prepare-worktree-context"
                )
            )
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), "old executable\n")

            second = subprocess.run(
                [str(INSTALLER)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )

            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn(f"Already linked {target}", second.stdout)


if __name__ == "__main__":
    unittest.main()
