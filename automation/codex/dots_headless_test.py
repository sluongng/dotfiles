"""Observable enrollment, routing/authentication and executor lifecycle checks."""
import base64
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import urllib.error

spec = importlib.util.spec_from_file_location("dots", Path(__file__).with_name("dots-headless.py"))
dots = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dots)


def token(account="account-one", user="user-one"):
    payload = {"https://api.openai.com/auth": {"chatgpt_account_id": account, "chatgpt_user_id": user}}
    return "header." + base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=") + ".signature"


class HeadlessDotsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        (self.home / "codex/skills").mkdir(parents=True)
        self.env = patch.dict(os.environ, {
            "XDG_STATE_HOME": str(self.home / "state"), "CODEX_HOME": str(self.home / "codex")
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.owner = {"accountId": "account-one", "userId": "user-one"}
        self.routing = {"chatgptAccountId": "account-one", "backendOrigin": "https://chatgpt.com",
                        "accountRoutingOverride": "NO_CONSTRAINT"}

    def command(self, command):
        output, error = io.StringIO(), io.StringIO()
        with patch.object(dots.sys, "argv", ["dots-headless", command]), contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = dots.main()
        return code, output.getvalue(), error.getvalue()

    def test_enrollment_is_stable_private_and_advertises_only_present_skills(self):
        bodies = []
        def request(method, path, body, **kwargs):
            bodies.append(body)
            self.assertEqual((method, path), ("POST", "/flora/cca/executor"))
            self.assertEqual(kwargs["expected"], self.owner)
            return {"executor_id": "executor-one"}
        with patch.object(dots, "authentication", return_value=(token(), self.owner, self.routing)), patch.object(dots, "request", side_effect=request):
            self.assertEqual(self.command("enroll")[0], 0)
            self.assertEqual(self.command("enroll")[0], 0)
        self.assertEqual(bodies[0], bodies[1])
        self.assertEqual(bodies[0]["selected_capability_roots"], [{"id": "codex-home-skills", "path": str(self.home / "codex/skills")}])
        for path in dots.state_dir().iterdir():
            self.assertEqual(path.stat().st_mode & 0o077, 0)
            self.assertNotIn(token(), path.read_text())

    def test_existing_enrollment_rejects_different_login_before_backend_write(self):
        dots.write_private(dots.state_dir() / "executor.json", {"owner": self.owner})
        with patch.object(dots, "authentication", return_value=(token("other"), {"accountId": "other", "userId": "user-one"}, self.routing)), patch.object(dots, "request") as request:
            code, _, error = self.command("enroll")
        self.assertEqual(code, 1)
        self.assertIn("another login", error)
        request.assert_not_called()

    def test_workspace_policy_and_identity_mismatch_fail_closed(self):
        for routing in (
            {**self.routing, "backendOrigin": "https://untrusted.example"},
            {**self.routing, "accountRoutingOverride": "us"},
            {**self.routing, "chatgptAccountId": "other"},
        ):
            with self.subTest(routing=routing), patch.object(dots, "rpc", side_effect=[
                {"account": {"type": "chatgpt"}, "workspaceRouting": routing},
                {"authMethod": "chatgpt", "authToken": token()},
            ]), patch.object(dots.urllib.request, "build_opener") as opener:
                code, _, error = self.command("enroll")
                self.assertEqual(code, 1)
                self.assertNotIn(token(), error)
                opener.assert_not_called()

    def test_unauthorized_refresh_preserves_identity_and_does_not_follow_redirects(self):
        reply = Mock()
        reply.__enter__ = Mock(return_value=reply)
        reply.__exit__ = Mock(return_value=False)
        reply.read.return_value = b'{"executor_id":"executor-one"}'
        opened = Mock()
        opened.open.side_effect = [urllib.error.HTTPError("https://chatgpt.com", 401, "denied", {}, None), reply]
        with patch.object(dots, "authentication", return_value=(token(), self.owner, self.routing)) as auth, patch.object(dots.urllib.request, "build_opener", return_value=opened):
            self.assertEqual(dots.request("GET", "/tbo", expected=self.owner), {"executor_id": "executor-one"})
        self.assertEqual(auth.call_args_list[0].args, (False,))
        self.assertEqual(auth.call_args_list[1].args, (True,))
        self.assertIsNone(dots.NoRedirect().redirect_request(None, None, 302, "", {}, "https://untrusted.example"))

    def test_refresh_cannot_switch_account(self):
        opened = Mock()
        opened.open.side_effect = urllib.error.HTTPError("https://chatgpt.com", 401, "denied", {}, None)
        with patch.object(dots, "authentication", side_effect=[(token(), self.owner, self.routing), (token("other"), {**self.owner, "accountId": "other"}, self.routing)]), patch.object(dots.urllib.request, "build_opener", return_value=opened):
            with self.assertRaisesRegex(dots.SetupError, "identity changed"):
                dots.request("GET", "/tbo", expected=self.owner)
        self.assertEqual(opened.open.call_count, 1)

    def test_backend_error_does_not_disclose_body_or_credentials(self):
        opened = Mock()
        opened.open.side_effect = urllib.error.HTTPError("https://chatgpt.com", 403, token(), {}, io.BytesIO(token().encode()))
        with patch.object(dots, "authentication", return_value=(token(), self.owner, self.routing)), patch.object(dots.urllib.request, "build_opener", return_value=opened):
            code, output, error = self.command("enroll")
        self.assertEqual(code, 1)
        self.assertIn("HTTP 403", error)
        self.assertNotIn(token(), output + error)

    def test_executor_passes_no_credentials_and_only_emits_allowlisted_diagnostics(self):
        state = {"owner": self.owner, "environmentId": "executor-one"}
        child = Mock()
        child.stderr = iter([
            f'unknown error Bearer {token()}\n',
            'INFO codex_exec_server::remote: noise_event="rendezvous_connection" noise_outcome="ok" secret="do-not-log"\n',
            json.dumps({"target": "codex_exec_server::remote", "fields": {"noise_event": "registration", "noise_outcome": "ok", "token": token()}}) + "\n",
        ])
        child.wait.return_value = 0
        with patch.object(dots, "enroll", return_value=state), patch.object(dots.subprocess, "Popen", return_value=child) as popen, patch.object(dots.signal, "signal"):
            code, output, error = self.command("run")
        self.assertEqual(code, 1)  # Unexpected clean exit must be restarted by systemd.
        self.assertIn('"noise_outcome": "ok"', output)
        self.assertNotIn(token(), output + error + repr(popen.call_args))
        self.assertNotIn("do-not-log", output)
        self.assertEqual(json.loads((dots.state_dir() / "transport.json").read_text())["exited"], 0)

    def test_service_stop_terminates_executor_without_failure(self):
        child = Mock()
        child.stderr = iter([])
        child.wait.return_value = 0
        handlers = {}
        def wait():
            handlers[dots.signal.SIGTERM](dots.signal.SIGTERM, None)
            return 0
        child.wait.side_effect = wait
        with patch.object(dots, "enroll", return_value={"environmentId": "executor-one"}), patch.object(dots.subprocess, "Popen", return_value=child), patch.object(dots.signal, "signal", side_effect=lambda name, fn: handlers.update({name: fn})):
            code, _, _ = self.command("run")
        self.assertEqual(code, 0)
        child.terminate.assert_called_once()

    def test_dot_attachment_never_replaces_existing_computers(self):
        state = {"owner": self.owner, "environmentId": "executor-one"}
        before = {"thread_id": "thread-one", "computers": [{"environment_id": "existing", "is_attached": True}]}
        after = {"thread_id": "thread-one", "computers": before["computers"] + [{"environment_id": "executor-one", "is_attached": True}]}
        with patch.object(dots, "dots", return_value=[{"id": "dot-one", "aeon_kind": "orbit", "status": "active", "scope": "personal", "active_root_thread_id": "thread-one"}]), patch.object(dots, "request", side_effect=[before, None, after]) as request:
            self.assertEqual(dots.connect(state), {"attached": True})
        post = request.call_args_list[1]
        self.assertEqual(post.args[0], "POST")
        self.assertIn("/connect?", post.args[1])
        self.assertNotIn("replace", post.args[1])

    def test_ambiguous_or_shared_dot_catalog_cannot_grant_access(self):
        for items in ([{"id": "shared", "aeon_kind": "orbit", "status": "active", "scope": "shared"}], [{"id": "missing-scope", "aeon_kind": "orbit", "status": "active"}]):
            with self.subTest(items=items), patch.object(dots, "dots", return_value=items), patch.object(dots, "request") as request:
                with self.assertRaisesRegex(dots.SetupError, "unambiguous"):
                    dots.connect({"owner": self.owner})
                request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
