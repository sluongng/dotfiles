#!/usr/bin/env python3
"""Publish curated chief-of-staff results privately; never export raw conversations."""
import argparse
import errno
from contextlib import closing, contextmanager
import fcntl
import hashlib
import html
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
from urllib.parse import unquote, urlsplit
import uuid

import markdown

TTL = 7 * 24 * 60 * 60
REPORT_LIMIT = 2 * 1024 * 1024
ASSET_LIMIT = 10 * 1024 * 1024
TEXT_TYPES = {'.md', '.txt', '.diff', '.patch', '.log', '.json', '.csv'}
IMAGE_TYPES = {'.png', '.jpg', '.jpeg', '.webp'}
ACTIVE = {'inprogress', 'in_progress', 'running', 'active', 'pending', 'queued'}
TERMINAL = {'completed', 'failed', 'interrupted'}
CSS = '''body{font:17px/1.6 system-ui,sans-serif;color:#24303e;background:#f4f6fa;margin:0}main{max-width:880px;margin:auto;padding:24px 20px 80px}article{background:white;padding:24px;border-radius:14px}h1,h2,h3{line-height:1.25;overflow-wrap:anywhere}h1{font-size:1.8rem}a{color:#1558a6;overflow-wrap:anywhere}pre{background:#152333;color:#eef4fa;padding:16px;border-radius:8px;overflow:auto;white-space:pre-wrap;word-break:break-word}code{overflow-wrap:anywhere}table{display:block;overflow:auto;border-collapse:collapse}td,th{padding:8px;border:1px solid #cbd3df}img{max-width:100%;height:auto}.meta,.local-only{color:#586777;font-size:.9rem}.warning{padding:12px;border-left:4px solid #a66d00;background:#fff3d8}li{margin:.4em 0}blockquote{border-left:3px solid #cbd3df;margin-left:0;padding-left:16px}@media(max-width:480px){main{padding:16px 10px}article{padding:16px}h1{font-size:1.5rem}}'''
CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"


def valid_id(value):
    return str(uuid.UUID(value))


def seconds(value):
    value = float(value or 0)
    return value / 1000 if value > 100_000_000_000 else value


def activity(codex_home, thread_id):
    """Unknown metadata is not evidence of inactivity, including a failed status read."""
    try:
        with closing(sqlite3.connect(f'file:{codex_home / "state_5.sqlite"}?mode=ro', uri=True, timeout=2)) as db:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM threads WHERE id=?', (thread_id,)).fetchone()
            if row is None:
                return {'known': False}
            values = dict(row)
            updated = seconds(values.get('updated_at_ms')) or seconds(values.get('updated_at'))
        with closing(sqlite3.connect(f'file:{codex_home / "thread_history_1.sqlite"}?mode=ro', uri=True, timeout=2)) as db:
            db.row_factory = sqlite3.Row
            turn = db.execute('SELECT * FROM thread_turns WHERE thread_id=? ORDER BY rollout_ordinal DESC LIMIT 1', (thread_id,)).fetchone()
            turn = dict(turn) if turn else {}
        updated = max(updated, seconds(turn.get('started_at')), seconds(turn.get('completed_at')))
        if not updated:
            return {'known': False}
        status = str(turn.get('status', '')).lower()
        if status not in ACTIVE | TERMINAL:
            return {'known': False}
        return {'known': True, 'last_activity': updated, 'active': status in ACTIVE}
    except (sqlite3.Error, OSError, ValueError):
        return {'known': False}


def safe_read(path, limit, source=True):
    """No symlinks, directories, secret stores, or uncontrolled large attachments."""
    path = Path(os.path.abspath(path))
    if source:
        parts = set(path.parts)
        sensitive = {'.codex', '.ssh', '.aws', '.gnupg', '.git', 'credentials', 'secrets'}
        if parts & sensitive or '/work/misc/finance/' in str(path) + '/':
            raise ValueError('Private source store cannot be published')
        if path.name.lower() in {'auth.json', 'credentials.json', '.env', 'id_rsa', 'id_ed25519'} or path.name.startswith('.env.'):
            raise ValueError('Credential file cannot be published')
    # Walk from a root descriptor, opening every ancestor without following links.
    # A path-level lstat followed by open() would race an ancestor replacement.
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parts[1:-1]:
            following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=directory)
            os.close(directory)
            directory = following
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directory)
    except (NotADirectoryError, OSError) as error:
        if error.errno in {errno.ENOTDIR, errno.ELOOP}:
            raise ValueError('Symlink sources are not publishable') from error
        raise
    finally:
        os.close(directory)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('Report source must be a bounded regular file')
        data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Report source exceeds size limit')
        return data


def page(title, content, warning=''):
    notice = f'<p class="warning">{html.escape(warning)}</p>' if warning else ''
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><style>{CSS}</style><main>'
            f'<article>{notice}{content}</article></main></html>').encode()


class Sanitizer(HTMLParser):
    TAGS = set('p h1 h2 h3 h4 h5 h6 ul ol li blockquote pre code em strong del hr br table thead tbody tr th td a img'.split())
    VOID = {'hr', 'br', 'img'}

    def __init__(self, report_dir, assets, prefix):
        super().__init__(convert_charrefs=True)
        self.report_dir, self.assets, self.prefix = report_dir, assets, prefix
        self.output, self.anchors = [], []

    def link(self, value, image=False):
        value = html.unescape(value or '').strip()
        value = re.sub(r'[\x00-\x20\x7f]', '', value)
        value = unquote(value)
        parsed = urlsplit(value)
        if parsed.scheme in {'http', 'https'} and parsed.netloc and not image:
            return value
        if value.startswith('#') and not image:
            return value
        if parsed.scheme and parsed.scheme != 'file':
            return None
        path = re.sub(r':\d+(?::\d+)?$', '', parsed.path)
        if not path or path.startswith('//'):
            return None
        candidate = Path(path) if path.startswith('/') else self.report_dir / path
        asset = self.assets.get(os.path.abspath(candidate))
        if asset and (not image or Path(asset).suffix.lower() in IMAGE_TYPES):
            return self.prefix + 'assets/' + asset + (('#' + parsed.fragment) if parsed.fragment else '')
        return None

    def handle_starttag(self, tag, attrs):
        if tag not in self.TAGS:
            return
        attrs = dict(attrs)
        if tag == 'a':
            link = self.link(attrs.get('href'))
            self.anchors.append(bool(link))
            self.output.append(f'<a href="{html.escape(link, quote=True)}" rel="noreferrer">' if link else '<span class="local-only">')
        elif tag == 'img':
            link = self.link(attrs.get('src'), image=True)
            if link:
                self.output.append(f'<img src="{html.escape(link, quote=True)}" alt="{html.escape(attrs.get("alt", ""), quote=True)}">')
        else:
            self.output.append('<' + tag + '>')

    def handle_endtag(self, tag):
        if tag == 'a':
            if self.anchors:
                self.output.append('</a>' if self.anchors.pop() else ' <small>(local-only; not shared)</small></span>')
        elif tag in self.TAGS and tag not in self.VOID:
            self.output.append('</' + tag + '>')

    def handle_data(self, text):
        self.output.append(html.escape(text))


def render(text, report_dir, assets, prefix):
    sanitizer = Sanitizer(report_dir, assets, prefix)
    sanitizer.feed(markdown.markdown(text, extensions=['tables', 'fenced_code']))
    sanitizer.close()
    return ''.join(sanitizer.output)


class Store:
    def __init__(self, state_dir, codex_home):
        self.root, self.codex_home = Path(state_dir), Path(codex_home)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink():
            raise ValueError('State directory cannot be a symlink')
        for part in ['registry', 'cache', 'locks']:
            (self.root / part).mkdir(mode=0o700, exist_ok=True)
            if (self.root / part).is_symlink():
                raise ValueError('State subdirectory cannot be a symlink')
        self.config = json.loads(safe_read(self.root / 'config.json', REPORT_LIMIT, source=False))
        url = urlsplit(self.config.get('base_url', ''))
        if not url.netloc or not self.config.get('owner_login'):
            raise ValueError('Configure base_url and owner_login before publishing')
        self.transport = self.config.get('transport', 'proxy')
        self.bind_host = '127.0.0.1'
        if self.transport == 'proxy':
            if url.scheme != 'https':
                raise ValueError('Proxy reports require an HTTPS base URL')
        elif self.transport == 'tailnet':
            status = tailscale_json('status')
            own = status.get('Self', {})
            self.bind_host = self.config.get('bind_host', '')
            hostname = own.get('DNSName', '').rstrip('.').casefold()
            if (self.bind_host not in own.get('TailscaleIPs', []) or not hostname
                    or not url.hostname or url.hostname.casefold() != hostname or url.scheme != 'http'
                    or url.port != 18841):
                raise ValueError('Direct reports must use this device tailnet IP and DNS port18841')
        else:
            raise ValueError('Unknown report transport')
        self.base_url = self.config['base_url'].rstrip('/') + '/'
        self.mount = url.path.rstrip('/')

    @contextmanager
    def lock(self, thread_id):
        fd = os.open(self.root / 'locks' / (valid_id(thread_id) + '.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def entry_path(self, thread_id):
        return self.root / 'registry' / (valid_id(thread_id) + '.json')

    def entry(self, thread_id):
        try:
            return json.loads(safe_read(self.entry_path(thread_id), REPORT_LIMIT, source=False))
        except FileNotFoundError:
            return None

    def write_entry(self, entry):
        path = self.entry_path(entry['thread_id'])
        fd, temporary = tempfile.mkstemp(prefix='.entry-', dir=path.parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(entry, stream, indent=2)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def url(self, thread_id):
        return self.base_url + 'threads/' + valid_id(thread_id) + '/'

    def cache_path(self, entry):
        generation = entry.get('generation')
        if not generation or not re.fullmatch(r'[0-9a-f]{32}', generation):
            return None
        return self.root / 'cache' / generation

    def expired(self, state, now):
        return state.get('known') and not state.get('active') and now - state['last_activity'] > TTL

    def remove_cache(self, entry):
        path = self.cache_path(entry)
        if path and path.exists():
            if path.is_symlink():
                raise ValueError('Refusing symlink cache')
            shutil.rmtree(path)
        entry.pop('generation', None)

    def build(self, entry):
        report = Path(entry['report'])
        text = safe_read(report, REPORT_LIMIT).decode('utf-8')
        if report.suffix.lower() != '.md':
            raise ValueError('Curated report must be Markdown')
        payloads, assets = {}, {}
        for source in entry['artifacts']:
            path = Path(source)
            if path.suffix.lower() not in TEXT_TYPES | IMAGE_TYPES:
                raise ValueError('Unsupported attachment type')
            payload = safe_read(path, ASSET_LIMIT)
            name = hashlib.sha256(str(path).encode()).hexdigest()[:12] + '-' + re.sub(r'[^a-zA-Z0-9._-]', '_', path.name)
            assets[str(path)] = name
            payloads[name] = (payload, path)
        generation = uuid.uuid4().hex
        directory = self.root / 'cache' / generation
        directory.mkdir(mode=0o700)
        committed = False
        try:
            (directory / 'assets').mkdir(mode=0o700)
            prefix = self.mount + '/threads/' + entry['thread_id'] + '/'
            content = render(text, report.parent, assets, prefix)
            (directory / 'index.html').write_bytes(page(entry['title'], content))
            for name, (payload, source) in payloads.items():
                if Path(name).suffix.lower() in TEXT_TYPES:
                    content = render(payload.decode('utf-8'), source.parent, assets, prefix) if name.lower().endswith('.md') else '<pre>' + html.escape(payload.decode('utf-8')) + '</pre>'
                    payload = page(name, content)
                (directory / 'assets' / name).write_bytes(payload)
            old = dict(entry)
            entry.update(generation=generation, assets=list(payloads), warning='', expired=False)
            self.write_entry(entry)
            committed = True
        except Exception:
            if not committed:
                shutil.rmtree(directory)
            raise
        try:
            self.remove_cache(old)
        except (OSError, ValueError):
            pass  # A committed new copy remains valid even if old-cache cleanup fails.

    def publish(self, thread_id, title, report, artifacts, now=None):
        now = time.time() if now is None else now
        entry = {'thread_id': valid_id(thread_id), 'title': title,
                 'report': os.path.abspath(report),
                 'artifacts': list(dict.fromkeys(os.path.abspath(x) for x in artifacts))}
        thread_id = entry['thread_id']
        with self.lock(thread_id):
            prior = self.entry(thread_id)
            if prior and prior.get('generation'):
                entry['generation'] = prior['generation']
            state = activity(self.codex_home, thread_id)
            entry['activity'] = state
            if self.expired(state, now):
                # Validate explicit inputs even when creating an expired registration.
                safe_read(entry['report'], REPORT_LIMIT)
                old = self.entry(thread_id)
                entry['expired'] = True
                self.write_entry(entry)
                if old:
                    self.remove_cache(old)
            else:
                self.build(entry)
        return {'thread_id': thread_id, 'url': self.url(thread_id), 'expired': entry.get('expired', False)}

    def refresh_locked(self, entry, now, regenerate):
        state = activity(self.codex_home, entry['thread_id'])
        entry['activity'] = state
        if self.expired(state, now):
            self.remove_cache(entry)
            entry['expired'] = True
            self.write_entry(entry)
            return entry
        if regenerate:
            try:
                self.build(entry)
            except (OSError, ValueError, UnicodeError):
                entry['warning'] = 'Source unavailable or unsafe; retained last published copy.'
                self.write_entry(entry)
        else:
            self.write_entry(entry)
        return entry

    def sync(self, now=None):
        results = []
        for path in sorted((self.root / 'registry').glob('*.json')):
            with self.lock(path.stem):
                entry = self.entry(path.stem)
                entry = self.refresh_locked(entry, time.time() if now is None else now, True)
                results.append({'thread_id': entry['thread_id'], 'expired': entry.get('expired', False), 'warning': entry.get('warning', '')})
        return results

    def response(self, path, now=None):
        """Exact registry routes only. Reads never count as thread activity."""
        now = time.time() if now is None else now
        path = unquote(urlsplit(path).path)
        if self.mount and (path == self.mount or path.startswith(self.mount + '/')):
            path = path[len(self.mount):] or '/'
        if '\\' in path or '\0' in path or any(x in {'.', '..'} for x in path.split('/')):
            return 404, 'text/plain', b'Not found'
        if path in {'/', '/index.html'}:
            items = []
            for record in sorted((self.root / 'registry').glob('*.json')):
                with self.lock(record.stem):
                    entry = self.refresh_locked(self.entry(record.stem), now, False)
                    if not entry.get('expired') and self.cache_path(entry):
                        items.append('<li><a href="' + html.escape(self.url(entry['thread_id']), quote=True) + '">' + html.escape(entry['title']) + '</a></li>')
            return 200, 'text/html; charset=utf-8', page('Chief of staff results', '<h1>Chief of staff results</h1><p class="meta">Private reading copies · expire after seven days of thread inactivity</p><ul>' + ''.join(items) + '</ul>')
        match = re.fullmatch(r'/threads/([0-9a-f-]{36})/(?:assets/([^/]+))?', path)
        if not match:
            return 404, 'text/plain', b'Not found'
        try:
            thread_id = valid_id(match[1])
        except ValueError:
            return 404, 'text/plain', b'Not found'
        with self.lock(thread_id):
            entry = self.entry(thread_id)
            if not entry:
                return 404, 'text/plain', b'Not found'
            entry = self.refresh_locked(entry, now, False)
            if entry.get('expired'):
                return 410, 'text/plain', b'This reading copy expired after seven days of thread inactivity. Original artifacts are unchanged.'
            directory = self.cache_path(entry)
            if not directory:
                return 404, 'text/plain', b'Reading copy unavailable'
            name = match[2]
            if name and name not in entry.get('assets', []):
                return 404, 'text/plain', b'Not found'
            target = directory / 'assets' / name if name else directory / 'index.html'
            try:
                payload = safe_read(target, ASSET_LIMIT + REPORT_LIMIT, source=False)
            except (OSError, ValueError):
                return 404, 'text/plain', b'Reading copy unavailable'
            mime = mimetypes.guess_type(name)[0] if name and Path(name).suffix.lower() in IMAGE_TYPES else 'text/html; charset=utf-8'
            warning = entry.get('warning', '')
            if not entry['activity'].get('known'):
                warning = 'Thread activity could not be verified; retained saved copy. ' + warning
            if warning and not name:
                payload = payload.replace(b'<article>', ('<article><p class="warning">' + html.escape(warning) + '</p>').encode(), 1)
            return 200, mime, payload


def tailscale_json(command, address=None):
    args = ['tailscale', command, '--json'] + ([address] if address else [])
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=3, check=True)
        return json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}


def authorized(store, address, headers):
    if store.transport == 'tailnet':
        # Never trust identity headers on a directly accessible listener.
        identity = tailscale_json('whois', address).get('UserProfile', {}).get('LoginName', '')
    else:
        identity = headers.get('Tailscale-User-Login', '')
    return bool(identity) and identity.casefold() == store.config['owner_login'].casefold()


def handler(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            if not authorized(store, self.client_address[0], self.headers):
                status, mime, payload = 403, 'text/plain', b'Private report: sign in through your Tailscale connection.'
            else:
                status, mime, payload = store.response(self.path)
            self.send_response(status)
            for key, value in {'Content-Type': mime, 'Content-Length': str(len(payload)), 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': CSP}.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(payload)
    return Handler


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, default=Path.home() / '.local/state/chief-of-staff-reports')
    parser.add_argument('--codex-home', type=Path, default=Path.home() / '.codex')
    sub = parser.add_subparsers(dest='command', required=True)
    publish = sub.add_parser('publish')
    publish.add_argument('--thread-id', required=True)
    publish.add_argument('--report', required=True, type=Path)
    publish.add_argument('--title', required=True)
    publish.add_argument('--artifact', action='append', default=[], type=Path)
    sub.add_parser('sync')
    serve = sub.add_parser('serve')
    serve.add_argument('--port', type=int, default=18841)
    args = parser.parse_args()
    try:
        store = Store(args.state_dir, args.codex_home)
        if args.command == 'publish':
            print(json.dumps(store.publish(args.thread_id, args.title, args.report, args.artifact)))
        elif args.command == 'sync':
            print(json.dumps({'reports': store.sync()}))
        else:
            if store.transport == 'tailnet' and args.port != 18841:
                raise ValueError('Direct reports use only the configured tailnet port18841')
            ThreadingHTTPServer((store.bind_host, args.port), handler(store)).serve_forever()
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f'Report operation failed: {type(error).__name__}; check source/configuration locally.\n')


if __name__ == '__main__':
    main()
