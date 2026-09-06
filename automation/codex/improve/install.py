#!/usr/bin/env python3
"""Install the bounded local improvement loop; enable only with --enable."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from observe import excluded_roots


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def unit_arg(value: Path | str) -> str:
    # systemd command quoting, including literal percent specifiers.
    return '"' + str(value).replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"') + '"'


def atomic_install(target: Path, content: str, backup: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and not target.is_symlink() and target.read_text() == content:
        return
    if os.path.lexists(target):
        saved = backup / target.relative_to(Path.home())
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, saved, follow_symlinks=False)
    fd, name = tempfile.mkstemp(prefix='.' + target.name, dir=target.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
        os.chmod(name, 0o600)
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enable', action='store_true')
    parser.add_argument('--exclude-root', action='append', default=[],
                        help='Persist a private thread exclusion in local state')
    args = parser.parse_args()
    home = Path.home()
    source = Path(__file__).resolve().parents[3]
    scripts = source / 'automation/codex/improve'
    state = home / '.local/state/codex-improve'
    units = home / '.config/systemd/user'
    aton = home / '.local/bin/codex-automaton'
    if not aton.is_file():
        raise SystemExit('Install Aton/codex-automaton before installing this loop.')
    # Never replace a definition or hook while its owner is executing.
    for unit in ('codex-observe.service', 'codex-automaton@codex-improve.service'):
        result = subprocess.run(['systemctl', '--user', 'is-active', unit], capture_output=True, text=True)
        if result.stdout.strip() in ('active', 'activating', 'deactivating'):
            raise SystemExit(f'{unit} is busy; finish that run before installing.')
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    state.chmod(0o700)
    backup = state / 'install-backups' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup.mkdir(parents=True, mode=0o700)
    if args.exclude_root:
        import re
        if any(not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value) for value in args.exclude_root):
            raise SystemExit('Invalid excluded thread ID.')
        exclusions = sorted(excluded_roots(state) | set(args.exclude_root))
        atomic_install(state / 'excluded-roots.json', json.dumps(exclusions) + '\n', backup)
    prefix = f'/usr/bin/python3 {unit_arg(scripts / "pipeline.py")} --state-dir {unit_arg(state)} --source-root {unit_arg(source)} --codex-home {unit_arg(home / ".codex")}'
    files = {
        'codex-observe.service': f'''[Unit]
Description=Collect incremental Codex evidence and local setup health

[Service]
Type=oneshot
UMask=0077
Nice=10
TimeoutStartSec=5min
KillMode=control-group
ExecStart=/usr/bin/python3 {unit_arg(scripts / 'observe.py')} --state-dir {unit_arg(state)} --source-root {unit_arg(source)} --codex-home {unit_arg(home / '.codex')}
''',
        'codex-observe.timer': '''[Unit]
Description=Daily incremental Codex observation

[Timer]
OnCalendar=*-*-* 06:45:00 Europe/Amsterdam
Persistent=true
RandomizedDelaySec=2min
Unit=codex-observe.service

[Install]
WantedBy=timers.target
''',
        'codex-automaton@codex-improve.service.d/improvement.conf': f'''[Service]
UMask=0077
Nice=10
TimeoutStartSec=20min
Environment=CODEX_HOME={unit_arg(home / '.codex')}
ExecCondition={prefix} gate
ExecStartPre={prefix} prepare
ExecStartPost={prefix} finish --result {unit_arg(home / '.local/state/codex-automaton/codex-improve/last-message.md')}
ExecStopPost=-/usr/bin/python3 {unit_arg(scripts / 'notify.py')} --state-dir {unit_arg(state)} --service-result ${{SERVICE_RESULT}}
''',
        'codex-improvement-check@.service': f'''[Unit]
Description=Validate Codex improvement candidate %i in scratch files

[Service]
Type=oneshot
UMask=0077
Nice=10
TimeoutStartSec=5min
KillMode=control-group
ExecStart={prefix} check %i
''',
    }
    for name, content in files.items():
        atomic_install(units / name, content, backup)
    # Job source is rendered with TOML string escaping, not shell interpolation.
    template = (source / 'config/codex/automations/codex-improve.toml.in').read_text()
    replacements = {
        '@SOURCE@': json.dumps(str(source)),
        '@SCHEMA@': json.dumps(str(state / 'review/result.schema.json')),
        '@CODEX@': json.dumps(shutil.which('codex') or '/usr/bin/codex'),
        '@PROMPT_PATH@': str(state / 'review/prompt.md'),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    staged = state / 'codex-improve.toml'
    atomic_install(staged, template, backup)
    # Save the pre-existing shared template and this one job before Aton renders.
    for target in (units / 'codex-automaton@.service', units / 'codex-automaton@codex-improve.timer', home / '.config/codex-automaton/automations/codex-improve.toml'):
        if os.path.lexists(target):
            saved = backup / target.relative_to(home)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved, follow_symlinks=False)
    # The generated hooks and backups use these exact roots. Do not let ambient
    # XDG/CODEX_AUTOMATON overrides send Aton to a different definition or output.
    run(str(aton), '--config-home', str(home / '.config/codex-automaton'),
        '--state-home', str(home / '.local/state/codex-automaton'),
        '--systemd-user-dir', str(units),
        'automation', 'install', str(staged), '--no-enable')
    run('systemctl', '--user', 'daemon-reload')
    run('systemd-analyze', '--user', 'verify', 'codex-observe.service', 'codex-observe.timer', 'codex-improvement-check@sample.service', 'codex-automaton@codex-improve.service')
    cli = home / '.local/bin/codex-improve'
    atomic_install(cli, '#!/bin/sh\nexec /usr/bin/python3 ' + "'" + str(scripts / 'pipeline.py').replace("'", "'\\''") + "'" + ' "$@"\n', backup)
    cli.chmod(0o700)
    if args.enable:
        run('systemctl', '--user', 'enable', '--now', 'codex-observe.timer', 'codex-automaton@codex-improve.timer')
    print(json.dumps({'installed': True, 'enabled': args.enable, 'state_dir': str(state), 'backup': str(backup)}))


if __name__ == '__main__':
    main()
