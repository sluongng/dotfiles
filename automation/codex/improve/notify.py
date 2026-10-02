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
    from pipeline import atomic_json, candidate_metrics, ledger, read_json
    receipt = args.state_dir / 'last-notification.json'
    previous = read_json(receipt) if receipt.exists() else {}
    sent = set(previous.get('keys', []))
    if previous.get('key'):
        sent.add(previous['key'])
    # Recovery closes the failure episode, including failures before a batch
    # exists. A later recurrence must be visible without repeating an ongoing
    # failure; proposal/overdue delivery receipts remain intact.
    if args.service_result == 'success':
        recovered = {key for key in sent if not key.startswith('failure:')}
        if recovered != sent:
            sent = recovered
            atomic_json(receipt, {'keys': sorted(sent)})
    notices = []
    chat_manifest = args.state_dir / 'retrospective/run/manifest.json'
    retrospective = (args.state_dir / 'retrospective').is_dir()
    manifest = chat_manifest if retrospective else args.state_dir / 'review/manifest.json'
    batch = read_json(manifest)['run_id' if retrospective else 'batch_id'] if manifest.exists() else 'before-preparation'
    history = args.state_dir / ('retrospective/history' if retrospective else 'history') / f'{batch}.json'
    failed = args.service_result not in ('success', 'exec-condition')
    if failed:
        notices.append((f'failure:{batch}:{args.service_result}', 'Codex improvement review failed',
                        'Evidence is retained. Inspect journalctl --user -u codex-automaton@codex-improve.service'))
    elif history.exists():
        record = read_json(history)
        count = len(record.get('result', {}).get('changed_files', [])) if retrospective else len(record.get('admitted_candidate_ids', []))
        if count:
            title = f'Codex retrospective: {count} file(s) improved' if retrospective else f'Codex improvement: {count} candidate(s) to review'
            notices.append((f'review:{batch}', title,
                            str(args.state_dir / 'latest.md')))
    # A proposal crossing seven days gets one notice per unresolved status,
    # even with no manifest/new evidence. Repeated weekly no-change runs stay quiet.
    overdue = [] if retrospective else candidate_metrics(args.state_dir, ledger(args.state_dir))['overdue_candidates']
    unsent = [entry for entry in overdue if f"overdue:{entry['candidate_id']}:{entry['status']}" not in sent]
    if unsent:
        keys = [f"overdue:{entry['candidate_id']}:{entry['status']}" for entry in unsent]
        notices.append((keys, f'Codex improvement: {len(unsent)} overdue proposal(s)',
                        'Decision or application pending for at least seven days. Run codex-improve status.'))
    binary = shutil.which('notify-send')
    if binary is None:
        return
    for key, title, body in notices:
        keys = key if isinstance(key, list) else [key]
        if all(item in sent for item in keys):
            continue
        result = subprocess.run([binary, '--app-name=Codex improvement', title, body], timeout=10, check=False)
        if result.returncode == 0:
            sent.update(keys)
            atomic_json(receipt, {'keys': sorted(sent)})


if __name__ == '__main__':
    main()
