"""Exercise the file opener against an isolated tmux server and real Neovim."""

import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import struct
import subprocess
import tempfile
import termios
import time
import unittest
import fcntl


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("open_file", ROOT / "open-file.py")
OPENER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OPENER)


class FileOpenerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="tmux-file-test-")
        cls.directory = Path(cls.temp.name)
        cls.bin = cls.directory / "bin"
        cls.bin.mkdir()
        cls.socket = cls.directory / "tmux.sock"
        for name, command in {
            "tmux": [shutil.which("tmux"), "-S", str(cls.socket)],
            "nvim": [shutil.which("nvim"), "-u", "NONE", "-i", "NONE"],
        }.items():
            wrapper = cls.bin / name
            wrapper.write_text("#!/bin/sh\nexec " + shlex.join(command) + ' "$@"\n')
            wrapper.chmod(0o700)
        cls.env = dict(os.environ, PATH=str(cls.bin) + ":" + os.environ["PATH"], TERM="xterm-256color",
                       XDG_RUNTIME_DIR=str(cls.directory), XDG_STATE_HOME=str(cls.directory / "state"),
                       XDG_DATA_HOME=str(cls.directory / "data"))
        cls.env.pop("TMUX", None)
        cls.tmux("-f", "/dev/null", "new-session", "-d", "-s", "test", "-x", "120", "-y", "30",
                 "-c", str(cls.directory), "sleep 300")
        cls.source = cls.tmux("display-message", "-p", "#{pane_id}")
        cls.tmux("set-option", "-g", "mouse", "on")
        cls.tmux("set-option", "-g", "prefix", "C-a")
        cls.tmux("set-option", "-g", "@fingers-cli", shutil.which("tmux-fingers"))
        cls.tmux("set-option", "-g", "@fingers-enable-bindings", "0")
        config = (ROOT.parent.parent / ".tmux.conf").read_text()
        snippet = config[config.index("# Open visible file paths"):config.index("bind F command-prompt")]
        bindings = cls.directory / "bindings.conf"
        bindings.write_text(snippet)
        cls.tmux("source-file", str(bindings))
        cls.tmux("run-shell", shlex.join([shutil.which("tmux-fingers"), "load-config"]))
        cls.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 120, 0, 0))
        cls.client = subprocess.Popen([str(cls.bin / "tmux"), "attach", "-t", "test"],
                                      stdin=slave, stdout=slave, stderr=slave, env=cls.env)
        os.close(slave)
        time.sleep(0.2)
        cls.drain()

    @classmethod
    def tearDownClass(cls):
        cls.tmux("kill-server")
        cls.client.wait(timeout=5)
        os.close(cls.master)
        cls.temp.cleanup()

    @classmethod
    def tmux(cls, *args):
        return subprocess.check_output([str(cls.bin / "tmux"), *args], env=cls.env,
                                       text=True, stderr=subprocess.PIPE).rstrip("\n")

    @classmethod
    def drain(cls):
        while select.select([cls.master], [], [], 0)[0]:
            os.read(cls.master, 65536)

    def setUp(self):
        self.file = self.directory / "response.md"
        self.file.write_text("first\nsecond line\nthird\n")

    def run_opener(self, path=None, *extra, input=None):
        args = ["python3", str(ROOT / "open-file.py"), "--pane", self.source, *extra]
        if path is not None:
            args.append(str(path))
        return subprocess.run(args, env=self.env, input=input, capture_output=True, text=True, timeout=20)

    def expression(self, editor, expression):
        socket = self.tmux("show-options", "-pqv", "-t", editor, "@file-editor-socket")
        return subprocess.check_output([str(self.bin / "nvim"), "--server", socket, "--remote-expr", expression],
                                       env=self.env, text=True).strip()

    def test_open_reuse_and_preserve_modified_buffer(self):
        # Even when another pane is active, the explicitly supplied source wins.
        other = self.tmux("new-window", "-d", "-P", "-F", "#{pane_id}", "sleep 300")
        self.tmux("select-window", "-t", other)
        result = self.run_opener("response.md:2:4", "--no-focus")
        self.assertEqual(result.returncode, 0, result.stderr)
        editor = result.stdout.strip()
        self.assertEqual(self.expression(editor, "expand('%:p')"), str(self.file))
        self.assertEqual(self.expression(editor, "line('.')"), "2")
        self.assertEqual(self.expression(editor, "col('.')"), "4")
        self.expression(editor, "luaeval(\"(function() vim.api.nvim_buf_set_lines(0,0,1,false,{'unsaved'}); return 1 end)()\")")
        second = self.directory / "second.md"
        second.write_text("another file\n")
        again = self.run_opener(second, "--no-focus")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(again.stdout.strip(), editor)
        payload = json.dumps(str(self.file)).replace("'", "''")
        self.assertEqual(self.expression(editor, f"getbufvar(bufnr(json_decode('{payload}')), '&modified')"), "1")
        self.assertEqual(self.file.read_text(), "first\nsecond line\nthird\n")
        self.assertEqual(self.tmux("display-message", "-p", "#{pane_id}"), other)

    def test_paths_with_spaces_quotes_and_shell_metacharacters(self):
        hostile = self.directory / "$(touch SENTINEL) user's note.md"
        hostile.write_text("safe\n")
        result = self.run_opener(hostile, "--no-focus")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.expression(result.stdout.strip(), "expand('%:p')"), str(hostile))
        self.assertFalse((self.directory / "SENTINEL").exists())

    def test_invalid_path_does_not_create_a_pane(self):
        before = self.tmux("list-panes", "-a", "-F", "#{pane_id}")
        result = self.run_opener("does-not-exist.md")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Not an existing file", result.stderr)
        self.assertEqual(self.tmux("list-panes", "-a", "-F", "#{pane_id}"), before)

    def test_keyboard_hints_open_a_wrapped_path(self):
        folder = self.directory / ("long-path-" * 10)
        folder.mkdir()
        path = folder / "reply.md"
        path.write_text("first\nsecond\n")
        self.tmux("select-window", "-t", self.source)
        self.tmux("select-pane", "-t", self.source)
        self.tmux("respawn-pane", "-k", "-t", self.source,
                  "printf '\033[2J\033[H%s\\n' " + shlex.quote(str(path) + ":2") + "; sleep 300")
        time.sleep(0.1)
        self.drain()
        os.write(self.master, b"\x01e")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            self.drain()
            if self.tmux("list-clients", "-F", "#{client_key_table}") == "fingers":
                break
            time.sleep(0.05)
        self.assertEqual(self.tmux("list-clients", "-F", "#{client_key_table}"), "fingers")
        # A single match receives "b" with the plugin's default qwerty layout.
        os.write(self.master, b"b")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            self.drain()
            editor = self.tmux("show-options", "-wqv", "-t", self.source, "@file-editor-pane")
            if editor and self.expression(editor, "expand('%:p')") == str(path):
                break
            time.sleep(0.05)
        self.assertEqual(self.expression(editor, "expand('%:p')"), str(path))
        self.assertEqual(self.expression(editor, "line('.')"), "2")

    def test_file_url_and_quoted_mouse_path(self):
        result = self.run_opener(self.file.as_uri() + "#L3", "--dry-run")
        self.assertEqual(json.loads(result.stdout), {"path": str(self.file), "line": 3, "column": 1})
        spaced = self.directory / "my note.md"
        spaced.write_text("text\n")
        text = f'• Open "{spaced}":2:3 next'
        location = OPENER.mouse_location(text, 12, self.directory)
        self.assertEqual(location, (spaced, 2, 3))
        self.assertEqual(OPENER.mouse_location(f"結果 {self.file}:3", 7, self.directory), (self.file, 3, 1))

    def test_ctrl_click_on_inactive_source_pane(self):
        # Render a real line and inject an SGR Ctrl-left-click via an attached PTY.
        folder = self.directory / ("mouse-wrap-" * 10)
        folder.mkdir()
        wrapped = folder / "wrapped.md"
        wrapped.write_text("first\nsecond\nthird\n")
        quoted = self.directory / "$(touch MOUSE_SENTINEL) user's note.md"
        quoted.write_text("first\nsecond\nthird\n")
        editor = self.tmux("show-options", "-wqv", "-t", self.source, "@file-editor-pane")
        if not editor:
            result = self.run_opener(self.file)
            self.assertEqual(result.returncode, 0, result.stderr)
            editor = result.stdout.strip()
        for name, path, label, copy_mode in [
            ("plain path", self.file, str(self.file) + ":3", False),
            ("wrapped path", wrapped, str(wrapped) + ":3", False),
            ("quoted shell data", quoted, f'"{quoted}":3', False),
            ("copy mode", self.file, str(self.file) + ":3", True),
        ]:
            with self.subTest(name=name):
                self.tmux("select-window", "-t", self.source)
                self.tmux("respawn-pane", "-k", "-t", self.source,
                          "printf '\033[2J\033[H%s\\n' " + shlex.quote(label) + "; sleep 300")
                # Distinct clicks, rather than tmux's double/triple-click events.
                time.sleep(0.4)
                if copy_mode:
                    self.tmux("copy-mode", "-t", self.source)
                self.tmux("select-pane", "-t", editor)
                position = int(self.tmux("display-message", "-p", "-t", self.source, "#{pane_left}")) + 4
                row = int(self.tmux("display-message", "-p", "-t", self.source, "#{pane_top}")) + 1
                self.drain()
                os.write(self.master, f"\033[<16;{position};{row}M\033[<16;{position};{row}m".encode())
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    self.drain()
                    if self.expression(editor, "expand('%:p')") == str(path) and self.expression(editor, "line('.')") == "3":
                        break
                    time.sleep(0.05)
                self.assertEqual(self.expression(editor, "expand('%:p')"), str(path))
                self.assertEqual(self.expression(editor, "line('.')"), "3")
                if copy_mode:
                    self.tmux("send-keys", "-t", self.source, "-X", "cancel")
            self.drain()
        self.assertFalse((self.directory / "MOUSE_SENTINEL").exists())


if __name__ == "__main__":
    unittest.main()
