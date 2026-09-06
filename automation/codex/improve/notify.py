#!/usr/bin/env python3
"""A local desktop notice for new review candidates or a failed review."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, default=Path.home() / '.local/state/codex-improve')
    parser.add_argument('--service-result', default='success')
    args = parser.parse_args()
    manifest = args.state_dir / 'review/manifest.json'
    if not manifest.exists():
        return
    batch = json.loads(manifest.read_text())['batch_id']
    history = args.state_dir / 'history' / f'{batch}.json'
    failed = args.service_result not in ('success', 'exec-condition')
    if failed:
        title = 'Codex improvement review failed'
        body = 'Evidence is retained. Inspect journalctl --user -u codex-automaton@codex-improve.service'
        key = f'failure:{batch}'
    elif history.exists():
        record = json.loads(history.read_text())
        # Model proposals can be duplicates of already accepted/rejected work.
        # Only the host's admitted IDs represent newly reviewable candidates.
        count = len(record.get('admitted_candidate_ids', []))
        if not count:
            return
        title = f'Codex improvement: {count} candidate(s) to review'
        body = str(args.state_dir / 'latest.md')
        key = f'review:{batch}'
    else:
        return
    receipt = args.state_dir / 'last-notification.json'
    if receipt.exists() and json.loads(receipt.read_text()).get('key') == key:
        return
    binary = shutil.which('notify-send')
    if binary is None:
        return
    result = subprocess.run([binary, '--app-name=Codex improvement', title, body], timeout=10, check=False)
    if result.returncode == 0:
        from pipeline import atomic_json
        atomic_json(receipt, {'key': key})


if __name__ == '__main__':
    main()
