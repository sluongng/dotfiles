#!/usr/bin/env python3

from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "automation/codex/check-config-privacy.py"
RENDERER = ROOT / "automation/codex/render-config.py"
PRE_PUSH = ROOT / ".githooks/pre-push"
CONFIG_PATH = Path("config/codex/config.toml")


class ConfigPrivacyTest(unittest.TestCase):
    def check_file(self, text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.toml"
            path.write_text(text)
            return subprocess.run(
                [sys.executable, str(CHECKER), "--file", str(path)],
                text=True,
                capture_output=True,
            )

    def init_repo(self, root: Path) -> None:
        subprocess.run(["git", "init", "-q", "-b", "master"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Config Privacy Test"],
            cwd=root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "config-privacy@example.invalid"],
            cwd=root,
            check=True,
        )
        (root / CONFIG_PATH.parent).mkdir(parents=True)

    def commit(self, root: Path, text: str, message: str) -> None:
        (root / CONFIG_PATH).write_text(text)
        subprocess.run(["git", "add", str(CONFIG_PATH)], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", message], cwd=root, check=True)

    def install_guard(self, root: Path) -> Path:
        checker = root / "automation/codex/check-config-privacy.py"
        hook = root / ".githooks/pre-push"
        checker.parent.mkdir(parents=True)
        hook.parent.mkdir(parents=True)
        shutil.copy2(CHECKER, checker)
        shutil.copy2(PRE_PUSH, hook)
        return hook

    def test_accepts_shared_config_without_project_tables(self) -> None:
        self.assertEqual(self.check_file('model = "gpt-5.6-sol"\n').returncode, 0)

    def test_rejects_active_and_commented_project_tables(self) -> None:
        samples = (
            "[projects]\n",
            '[projects."/local/project"]\ntrust_level = "trusted"\n',
            '["projects"."/local/project"]\ntrust_level = "trusted"\n',
            '# [projects."/local/project"]\n# trust_level = "trusted"\n',
            '## [projects."/local/project"]\n# trust_level = "trusted"\n',
        )
        for sample in samples:
            with self.subTest(sample=sample):
                result = self.check_file(sample)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("/local/project", result.stderr)

    def test_renderer_rejects_commented_project_tables(self) -> None:
        reject_projects_table = runpy.run_path(str(RENDERER))[
            "reject_projects_table"
        ]

        with self.assertRaises(SystemExit):
            reject_projects_table(
                Path("shared config"),
                '# [projects."/local/project"]\n# trust_level = "trusted"\n',
            )

    def test_staged_check_reads_the_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.init_repo(root)
            self.commit(root, 'model = "safe"\n', "safe")
            (root / CONFIG_PATH).write_text(
                '# [projects."/local/project"]\n# trust_level = "trusted"\n'
            )
            subprocess.run(["git", "add", str(CONFIG_PATH)], cwd=root, check=True)
            (root / CONFIG_PATH).write_text('model = "safe"\n')

            result = subprocess.run(
                [sys.executable, str(CHECKER), "--staged"],
                cwd=root,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("/local/project", result.stderr)

    def test_history_check_catches_a_removed_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.init_repo(root)
            self.commit(
                root,
                '[projects."/local/project"]\ntrust_level = "trusted"\n',
                "add private project",
            )
            self.commit(root, 'model = "safe"\n', "remove private project")

            result = subprocess.run(
                [sys.executable, str(CHECKER), "--history", "HEAD"],
                cwd=root,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("commit ", result.stderr)
            self.assertNotIn("/local/project", result.stderr)

    def test_pre_push_checks_only_commits_after_remote_tip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.init_repo(root)
            self.commit(
                root,
                '[projects."/legacy/project"]\ntrust_level = "trusted"\n',
                "legacy remote commit",
            )
            remote_oid = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            self.commit(root, 'model = "safe"\n', "clean history")
            local_oid = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            hook = self.install_guard(root)

            result = subprocess.run(
                [str(hook), "origin", "unused"],
                cwd=root,
                input=(
                    f"refs/heads/master {local_oid} "
                    f"refs/heads/master {remote_oid}\n"
                ),
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

    def test_pre_push_checks_hidden_commits_on_a_new_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.init_repo(root)
            self.commit(root, 'model = "safe"\n', "remote base")
            remote_oid = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            subprocess.run(
                ["git", "update-ref", "refs/remotes/origin/master", remote_oid],
                cwd=root,
                check=True,
            )
            self.commit(
                root,
                '# [projects."/local/project"]\n# trust_level = "trusted"\n',
                "add private project",
            )
            self.commit(root, 'model = "safe"\n', "hide private project")
            local_oid = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            hook = self.install_guard(root)

            result = subprocess.run(
                [str(hook), "origin", "unused"],
                cwd=root,
                input=(
                    f"refs/heads/topic {local_oid} "
                    f"refs/heads/topic {'0' * 40}\n"
                    f"refs/heads/deleted {'0' * 40} "
                    f"refs/heads/deleted {remote_oid}\n"
                ),
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("commit ", result.stderr)
            self.assertNotIn("/local/project", result.stderr)


if __name__ == "__main__":
    unittest.main()
