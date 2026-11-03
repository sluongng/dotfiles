"""Observable private report delivery, authorization and retention tests."""
from contextlib import closing
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch
import os

import chief_reports as reports


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'
        self.state.mkdir()
        (self.state / 'config.json').write_text(json.dumps({'base_url': 'https://device.example.ts.net/chief-of-staff/', 'owner_login': 'owner@example.test'}))
        self.codex = self.root / 'codex'
        self.codex.mkdir()
        self.thread = str(uuid.uuid4())
        self.now = 2_000_000_000
        with closing(sqlite3.connect(self.codex / 'state_5.sqlite')) as db, db:
            db.execute('CREATE TABLE threads(id TEXT PRIMARY KEY,updated_at INTEGER,updated_at_ms INTEGER)')
            db.execute('INSERT INTO threads VALUES(?,?,?)', (self.thread, self.now - 100, (self.now - 100) * 1000))
        with closing(sqlite3.connect(self.codex / 'thread_history_1.sqlite')) as db, db:
            db.execute('CREATE TABLE thread_turns(thread_id TEXT,rollout_ordinal INTEGER,status TEXT,started_at INTEGER,completed_at INTEGER)')
            db.execute('INSERT INTO thread_turns VALUES(?,1,?,?,?)', (self.thread, 'completed', self.now - 100, self.now - 100))
        self.report = self.root / 'result.md'
        self.report.write_text('# Source context\n\n[Slack](https://example.test/thread)\n\n## Result\n\nUseful finding.')
        self.store = reports.Store(self.state, self.codex)

    def tearDown(self):
        self.temp.cleanup()

    def publish(self, artifacts=()):
        return self.store.publish(self.thread, 'Useful result', self.report, artifacts, self.now)

    def get(self, suffix=''):
        return self.store.response('/chief-of-staff/threads/' + self.thread + '/' + suffix, self.now)

    def set_activity(self, age, status='completed'):
        stamp = self.now - age
        with closing(sqlite3.connect(self.codex / 'state_5.sqlite')) as db, db:
            db.execute('UPDATE threads SET updated_at=?,updated_at_ms=? WHERE id=?', (stamp, stamp * 1000, self.thread))
        with closing(sqlite3.connect(self.codex / 'thread_history_1.sqlite')) as db, db:
            db.execute('UPDATE thread_turns SET started_at=?,completed_at=?,status=? WHERE thread_id=?', (stamp, stamp, status, self.thread))

    def test_http_owner_access_and_denial_positive_control(self):
        self.publish()
        server = ThreadingHTTPServer(('127.0.0.1', 0), reports.handler(self.store))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            for identity, expected in [(None, 403), ('other@example.test', 403), ('owner@example.test', 200)]:
                connection = HTTPConnection('127.0.0.1', server.server_port)
                connection.request('GET', '/chief-of-staff/threads/' + self.thread + '/', headers={'Tailscale-User-Login': identity} if identity else {})
                response = connection.getresponse()
                payload = response.read()
                self.assertEqual(response.status, expected)
                self.assertEqual(response.getheader('Cache-Control'), 'no-store')
                self.assertIn("default-src 'none'", response.getheader('Content-Security-Policy'))
                if expected == 200:
                    self.assertIn(b'Useful finding', payload)
                connection.close()
            connection = HTTPConnection('127.0.0.1', server.server_port)
            connection.request('POST', '/', body=b'change')
            self.assertEqual(connection.getresponse().status, 501)
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_direct_transport_is_tailnet_bound_and_ignores_identity_headers(self):
        config = {'transport': 'tailnet', 'bind_host': '100.64.1.2',
                  'base_url': 'http://device.example.ts.net:18841/',
                  'owner_login': 'owner@example.test'}
        status = {'Self': {'TailscaleIPs': ['100.64.1.2'], 'DNSName': 'device.example.ts.net.'}}
        (self.state / 'config.json').write_text(json.dumps(config))
        with patch.object(reports, 'tailscale_json', return_value=status):
            direct = reports.Store(self.state, self.codex)
        self.assertEqual(direct.bind_host, '100.64.1.2')
        for identity, expected in [('owner@example.test', True), ('other@example.test', False), ('', False)]:
            with patch.object(reports, 'tailscale_json', return_value={'UserProfile': {'LoginName': identity}}) as whois:
                self.assertEqual(reports.authorized(direct, '100.64.9.8', {'Tailscale-User-Login': 'owner@example.test'}), expected)
                whois.assert_called_once_with('whois', '100.64.9.8')
        for field, value in [('bind_host', '0.0.0.0'), ('bind_host', '192.168.1.2'), ('base_url', 'http://other.example.ts.net:18841/')]:
            bad = dict(config, **{field: value})
            (self.state / 'config.json').write_text(json.dumps(bad))
            with patch.object(reports, 'tailscale_json', return_value=status), self.assertRaises(ValueError):
                reports.Store(self.state, self.codex)

    def test_markdown_links_declared_attachments_and_external_port(self):
        artifact = self.root / 'details.md'
        artifact.write_text('# Detail\n\nA useful proof.')
        patch = self.root / 'change.patch'
        patch.write_text('--- before\n+++ after\n+fixed')
        self.report.write_text(f'# Context\n\n[relative](details.md) [absolute]({artifact}:12) [patch]({patch}) [unshared](/etc/passwd) [source](https://example.test:8443/thread)')
        result = self.publish([artifact, patch])
        self.assertTrue(result['url'].endswith('/threads/' + self.thread + '/'))
        status, _, body = self.get()
        self.assertEqual(status, 200)
        self.assertNotIn(b'href="/etc/passwd"', body)
        self.assertNotIn(str(artifact).encode(), body)
        self.assertIn(b'local-only; not shared', body)
        self.assertIn(b'href="https://example.test:8443/thread"', body)
        entry = self.store.entry(self.thread)
        for name in entry['assets']:
            status, mime, payload = self.get('assets/' + name)
            self.assertEqual(status, 200)
            self.assertIn('text/html', mime)
            self.assertTrue(b'A useful proof' in payload or b'+fixed' in payload)

    def test_markdown_and_raw_html_cannot_execute(self):
        self.report.write_text('''# Title
<script>alert('raw')</script><iframe src="https://bad.test"></iframe>
<a href="jav&#97;script:alert(1)" onclick="alert(2)">raw link</a>
[bad](javascript:alert%281%29) [encoded](%6aavascript:alert%281%29)
<img src="https://tracker.test/a" onerror="alert(3)">
[good](https://example.test/thread)
''')
        self.publish()
        _, _, body = self.get()
        for forbidden in [b'<script', b'<iframe', b'onclick=', b'onerror=', b'href="javascript:', b'src="https://tracker']:
            self.assertNotIn(forbidden, body)
        self.assertIn(b'href="https://example.test/thread"', body)

    def test_paths_traversal_symlinks_and_failed_publish_preserve_prior(self):
        artifact = self.root / 'proof.txt'
        artifact.write_text('allowed proof')
        self.publish([artifact])
        asset = self.store.entry(self.thread)['assets'][0]
        self.assertEqual(self.get('assets/' + asset)[0], 200)
        for suffix in ['assets/../../manifest.json', 'assets/%2e%2e/secret', 'assets/%252e%252e', 'assets/unregistered.txt']:
            self.assertEqual(self.get(suffix)[0], 404)
        symlink = self.root / 'link.txt'
        symlink.symlink_to(artifact)
        with self.assertRaises(ValueError):
            self.publish([symlink])
        self.assertEqual(self.get('assets/' + asset)[0], 200)
        target = self.store.cache_path(self.store.entry(self.thread)) / 'assets' / asset
        target.unlink()
        target.symlink_to(artifact)
        self.assertEqual(self.get('assets/' + asset)[0], 404)

    def test_retention_boundary_republish_cleans_all_copies_and_preserves_sources(self):
        artifact = self.root / 'retained-proof.txt'
        artifact.write_text('source evidence')
        self.publish([artifact])
        first = self.store.cache_path(self.store.entry(self.thread))
        self.publish()
        self.assertFalse(first.exists())
        self.assertEqual(len(list((self.state / 'cache').iterdir())), 1)
        self.set_activity(reports.TTL)
        self.assertEqual(self.get()[0], 200)
        self.set_activity(reports.TTL + 1)
        self.assertEqual(self.get()[0], 410)
        self.assertTrue(self.report.exists())
        self.assertTrue(artifact.exists())
        self.assertEqual(list((self.state / 'cache').iterdir()), [])
        self.set_activity(0)
        self.store.sync(self.now)
        self.assertEqual(self.get()[0], 200)

    def test_render_and_reads_do_not_extend_expiration(self):
        self.set_activity(reports.TTL - 1)
        self.publish()
        self.assertEqual(self.get()[0], 200)
        self.store.sync(self.now)
        self.assertEqual(self.store.response('/threads/' + self.thread + '/', self.now + 2)[0], 410)

    def test_active_and_unavailable_metadata_are_not_pruned(self):
        self.publish()
        self.set_activity(reports.TTL + 100, 'inProgress')
        self.assertEqual(self.get()[0], 200)
        (self.codex / 'thread_history_1.sqlite').unlink()
        self.assertEqual(self.get()[0], 200)
        self.assertIn(b'activity could not be verified', self.get()[2])
        self.assertTrue(self.store.cache_path(self.store.entry(self.thread)).is_dir())

    def test_missing_or_unknown_turn_status_does_not_prove_inactivity(self):
        self.publish()
        self.set_activity(reports.TTL + 100)
        with closing(sqlite3.connect(self.codex / 'thread_history_1.sqlite')) as db, db:
            db.execute('DELETE FROM thread_turns')
        self.assertEqual(self.get()[0], 200)
        with closing(sqlite3.connect(self.codex / 'thread_history_1.sqlite')) as db, db:
            db.execute('INSERT INTO thread_turns VALUES(?,1,?,?,?)',
                       (self.thread, 'futureUnknownStatus', self.now - reports.TTL - 100,
                        self.now - reports.TTL - 100))
        self.assertEqual(self.get()[0], 200)
        self.set_activity(reports.TTL + 100, 'completed')
        self.assertEqual(self.get()[0], 410)

    def test_ancestor_replacement_cannot_redirect_source_read(self):
        source = self.root / 'source'
        source.mkdir()
        (source / 'proof.txt').write_text('declared content')
        private = self.root / 'private'
        private.mkdir()
        (private / 'proof.txt').write_text('private payload')
        self.assertEqual(reports.safe_read(source / 'proof.txt', 100), b'declared content')
        original_open = os.open
        swapped = False

        def race(path, flags, *args, **kwargs):
            nonlocal swapped
            if path == 'proof.txt' and not swapped:
                swapped = True
                source.rename(self.root / 'original-source')
                source.symlink_to(private, target_is_directory=True)
            return original_open(path, flags, *args, **kwargs)

        with patch.object(reports.os, 'open', side_effect=race):
            payload = reports.safe_read(source / 'proof.txt', 100)
        self.assertTrue(swapped)
        self.assertEqual(payload, b'declared content')
        with self.assertRaises(ValueError):
            reports.safe_read(source / 'proof.txt', 100)

    def test_source_missing_retains_last_good_copy_and_warns(self):
        self.publish()
        self.report.unlink()
        self.store.sync(self.now)
        self.assertEqual(self.get()[0], 200)
        self.assertIn(b'Source unavailable', self.get()[2])
        self.assertIn(b'Useful finding', self.get()[2])

    def test_finance_secrets_and_active_file_types_are_not_exported(self):
        self.publish()
        for name in ['auth.json', '.env', 'page.html', 'drawing.svg']:
            path = self.root / name
            path.write_text('must not publish')
            with self.assertRaises(ValueError):
                self.publish([path])
        finance = self.root / 'work/misc/finance/proof.md'
        finance.parent.mkdir(parents=True)
        finance.write_text('household proof')
        with self.assertRaises(ValueError):
            self.publish([finance])
        self.assertEqual(self.get()[0], 200)


if __name__ == '__main__':
    unittest.main()
