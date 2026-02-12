#!/usr/bin/env python3
"""Generate a replay-ready `bb execute` command from a BuildBuddy invocation.

This helper resolves one action from an invocation, downloads Action+Command
protos via `bb download`, and prints a fully formed `bb execute` command.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any


INVOCATION_ID_RE = re.compile(
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)


def eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate replay-ready `bb execute` command for one BuildBuddy action."
    )
    parser.add_argument(
        "--invocation",
        required=True,
        help="Invocation UUID or BuildBuddy invocation URL.",
    )
    parser.add_argument(
        "--group-id",
        default=os.environ.get("BB_GROUP_ID", ""),
        help="BuildBuddy group ID. Can also be set via BB_GROUP_ID.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BB_BASE_URL", "https://app.buildbuddy.io"),
        help="BuildBuddy app base URL for RPC calls.",
    )
    parser.add_argument(
        "--grpc-target",
        default=os.environ.get("BB_GRPC_TARGET", ""),
        help="gRPC target used by `bb download` (host:port). Auto-derived if not set.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("BB_API_KEY", ""),
        help="BuildBuddy API key. Defaults to BB_API_KEY, then git config.",
    )
    parser.add_argument(
        "--api-key-in-command",
        action="store_true",
        help="Embed the API key directly in the generated command (not recommended).",
    )
    parser.add_argument(
        "--execution-id",
        default="",
        help="Execution ID selector.",
    )
    parser.add_argument(
        "--action-digest-hash",
        default="",
        help="Action digest hash selector.",
    )
    parser.add_argument(
        "--target-label",
        default="",
        help="Target label selector (ex: //foo:bar).",
    )
    parser.add_argument(
        "--mnemonic",
        default="",
        help="Action mnemonic selector (ex: CppCompile).",
    )
    parser.add_argument(
        "--primary-output",
        default="",
        help="Primary output path selector.",
    )
    parser.add_argument(
        "--pin-executor-id",
        default="",
        help="Set exec property debug-executor-id to this executor ID.",
    )
    parser.add_argument(
        "--pin-worker-host-id",
        default="",
        help="Map this executor host ID to executor ID and pin to it.",
    )
    parser.add_argument(
        "--pin-to-original-worker",
        action="store_true",
        help="Map selected execution worker host ID to executor ID and pin to it.",
    )
    parser.add_argument(
        "--set-action-env",
        action="append",
        default=[],
        help="Override or add action env var: NAME=VALUE. Repeatable.",
    )
    parser.add_argument(
        "--remove-action-env",
        action="append",
        default=[],
        help="Remove action env var by NAME. Repeatable.",
    )
    parser.add_argument(
        "--set-exec-property",
        action="append",
        default=[],
        help="Override or add exec property: NAME=VALUE. Repeatable.",
    )
    parser.add_argument(
        "--remove-exec-property",
        action="append",
        default=[],
        help="Remove exec property by NAME. Repeatable.",
    )
    parser.add_argument(
        "--arg",
        dest="arg_override",
        action="append",
        default=[],
        help="Replace command arguments. Repeatable; if set, original args are ignored.",
    )
    parser.add_argument(
        "--new-invocation-id",
        action="store_true",
        help="Set --invocation_id to a fresh UUID instead of original invocation ID.",
    )
    parser.add_argument(
        "--omit-invocation-id",
        action="store_true",
        help="Do not set --invocation_id in the generated command.",
    )
    parser.add_argument(
        "--output-file",
        default="",
        help="Write generated command to this file instead of stdout.",
    )
    parser.add_argument(
        "--selection-json",
        default="",
        help="Write selected execution JSON to this file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print extra diagnostics to stderr.",
    )
    args = parser.parse_args()

    if not args.group_id:
        parser.error("--group-id is required (or set BB_GROUP_ID).")
    if args.new_invocation_id and args.omit_invocation_id:
        parser.error("--new-invocation-id and --omit-invocation-id are incompatible.")
    pin_opts = [bool(args.pin_executor_id), bool(args.pin_worker_host_id), bool(args.pin_to_original_worker)]
    if sum(1 for x in pin_opts if x) > 1:
        parser.error("Only one of --pin-executor-id, --pin-worker-host-id, --pin-to-original-worker may be set.")
    return args


def extract_invocation_id(text: str) -> str:
    m = INVOCATION_ID_RE.search(text)
    if not m:
        raise ValueError(f"Could not parse invocation ID from: {text}")
    return m.group(1).lower()


def load_api_key(cli_value: str) -> str:
    if cli_value:
        return cli_value
    env_value = os.environ.get("BB_API_KEY", "").strip()
    if env_value:
        return env_value
    try:
        value = subprocess.check_output(
            ["git", "config", "--local", "buildbuddy.api-key"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        value = ""
    if value:
        return value
    raise RuntimeError("Missing API key. Pass --api-key, set BB_API_KEY, or run `bb login`.")


def call_rpc(base_url: str, api_key: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/rpc/BuildBuddyService/{method}"
    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-buildbuddy-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} failed ({e.code}): {err_body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"{method} request failed: {e}") from e
    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{method} returned invalid JSON: {e}") from e


def parse_target_from_executor(remote_executor: str) -> str:
    target = remote_executor.strip()
    target = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", target)
    if "/" in target:
        target = target.split("/", 1)[0]
    return target


def get_canonical_options(get_invocation_rsp: dict[str, Any]) -> dict[str, str]:
    invocations = get_invocation_rsp.get("invocation", [])
    if not invocations:
        raise RuntimeError("GetInvocation returned no invocation records.")
    scl = invocations[0].get("structuredCommandLine", [])
    if not scl:
        return {}
    canonical = next((cl for cl in scl if cl.get("commandLineLabel") == "canonical"), scl[0])
    out: dict[str, str] = {}
    for section in canonical.get("sections", []):
        for opt in section.get("optionList", {}).get("option", []):
            name = opt.get("optionName")
            value = opt.get("optionValue")
            if name and value is not None:
                out[name] = str(value)
    return out


def digest_str(d: dict[str, Any] | None) -> str:
    if not d:
        return ""
    h = d.get("hash", "")
    size = d.get("sizeBytes", "")
    return f"{h}/{size}" if h != "" and size != "" else ""


def summarize_execution(e: dict[str, Any]) -> str:
    return (
        f"execution_id={e.get('executionId','')} "
        f"action_digest={digest_str(e.get('actionDigest'))} "
        f"target={e.get('targetLabel','')} "
        f"mnemonic={e.get('actionMnemonic','')} "
        f"primary_output={e.get('primaryOutputPath','')} "
        f"status_code={e.get('status',{}).get('code', 0)} "
        f"exit_code={e.get('exitCode', 0)} "
        f"worker={e.get('executedActionMetadata',{}).get('worker','')}"
    )


def choose_execution(executions: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    filtered = executions
    if args.execution_id:
        filtered = [e for e in filtered if e.get("executionId", "") == args.execution_id]
    if args.action_digest_hash:
        filtered = [e for e in filtered if e.get("actionDigest", {}).get("hash", "") == args.action_digest_hash]
    if args.target_label:
        filtered = [e for e in filtered if e.get("targetLabel", "") == args.target_label]
    if args.mnemonic:
        filtered = [e for e in filtered if e.get("actionMnemonic", "") == args.mnemonic]
    if args.primary_output:
        filtered = [e for e in filtered if e.get("primaryOutputPath", "") == args.primary_output]

    selectors_used = any(
        bool(x)
        for x in [
            args.execution_id,
            args.action_digest_hash,
            args.target_label,
            args.mnemonic,
            args.primary_output,
        ]
    )

    if len(filtered) == 1:
        return filtered[0]
    if len(filtered) == 0:
        raise RuntimeError("No execution matched the provided selectors.")

    if not selectors_used and len(executions) == 1:
        return executions[0]

    eprint("Multiple executions matched. Refine with one of:")
    eprint("  --execution-id, --action-digest-hash, or --target-label/--mnemonic/--primary-output")
    for i, e in enumerate(filtered, start=1):
        eprint(f"  [{i}] {summarize_execution(e)}")
    raise RuntimeError("Execution selector is ambiguous.")


def parse_key_value(raw: str, flag_name: str) -> tuple[str, str]:
    if "=" not in raw:
        raise RuntimeError(f"{flag_name} expects NAME=VALUE (got: {raw})")
    name, value = raw.split("=", 1)
    name = name.strip()
    if not name:
        raise RuntimeError(f"{flag_name} expects non-empty NAME (got: {raw})")
    return name, value


def kv_list_to_ordered_map(items: list[tuple[str, str]]) -> tuple[list[str], dict[str, str]]:
    order: list[str] = []
    data: dict[str, str] = {}
    for k, v in items:
        if k not in data:
            order.append(k)
        data[k] = v
    return order, data


def apply_overrides(
    items: list[tuple[str, str]],
    remove_keys: list[str],
    set_items: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    order, data = kv_list_to_ordered_map(items)
    for k in remove_keys:
        if k in data:
            del data[k]
    for k, v in set_items:
        if k not in data:
            order.append(k)
        data[k] = v
    return [(k, data[k]) for k in order if k in data]


def cas_resource_name(instance_name: str, digest_function: str, digest: dict[str, Any]) -> str:
    h = digest.get("hash", "")
    size = digest.get("sizeBytes", "")
    if not h or size in ("", None):
        raise RuntimeError(f"Invalid digest: {digest}")
    fn = (digest_function or "sha256").lower()
    parts: list[str] = []
    normalized_instance = instance_name.strip("/")
    if normalized_instance:
        parts.append(normalized_instance)
    parts.append("blobs")
    if fn != "sha256":
        parts.append(fn)
    parts.extend([h, str(size)])
    return "/".join(parts)


def run_command(argv: list[str], verbose: bool = False) -> str:
    if verbose:
        eprint("+ " + " ".join(shlex.quote(a) for a in argv))
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(shlex.quote(a) for a in argv)
            + f"\nexit={p.returncode}\nstdout:\n{p.stdout}\nstderr:\n{p.stderr}"
        )
    return p.stdout


def download_proto_json(
    bb_type: str,
    digest: dict[str, Any],
    *,
    instance_name: str,
    digest_function: str,
    grpc_target: str,
    api_key: str,
    verbose: bool,
) -> dict[str, Any]:
    resource = cas_resource_name(instance_name, digest_function, digest)
    stdout = run_command(
        [
            "bb",
            "download",
            resource,
            "--type",
            bb_type,
            "--target",
            grpc_target,
            "--remote_header",
            f"x-buildbuddy-api-key={api_key}",
        ],
        verbose=verbose,
    )
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"`bb download` returned invalid JSON for {bb_type}: {e}") from e


def resolve_executor_id_for_host(
    *,
    base_url: str,
    api_key: str,
    group_id: str,
    host_id: str,
) -> str:
    if not host_id:
        raise RuntimeError("Cannot resolve executor ID from empty host ID.")
    rsp = call_rpc(
        base_url,
        api_key,
        "GetExecutionNodes",
        {"requestContext": {"groupId": group_id}},
    )
    matches = [
        ex for ex in rsp.get("executor", []) if ex.get("node", {}).get("executorHostId", "") == host_id
    ]
    if len(matches) == 1:
        return matches[0].get("node", {}).get("executorId", "")
    if len(matches) == 0:
        raise RuntimeError(f"No executor found with executor_host_id={host_id}")
    ids = [m.get("node", {}).get("executorId", "") for m in matches]
    raise RuntimeError(f"Multiple executors matched host ID {host_id}: {ids}")


def format_shell_command(parts: list[str], unquoted_indexes: set[int]) -> str:
    out: list[str] = []
    for i, part in enumerate(parts):
        out.append(part if i in unquoted_indexes else shlex.quote(part))
    return " \\\n\t".join(out)


def main() -> int:
    args = parse_args()
    try:
        invocation_id = extract_invocation_id(args.invocation)
        api_key = load_api_key(args.api_key)

        get_invocation_rsp = call_rpc(
            args.base_url,
            api_key,
            "GetInvocation",
            {
                "requestContext": {"groupId": args.group_id},
                "lookup": {"invocationId": invocation_id},
            },
        )
        options = get_canonical_options(get_invocation_rsp)

        remote_executor = options.get("remote_executor") or options.get("remote_cache", "")
        remote_instance = options.get("remote_instance_name", "")
        digest_function = (options.get("digest_function", "sha256") or "sha256").lower()
        grpc_target = args.grpc_target or (parse_target_from_executor(remote_executor) if remote_executor else "")
        if not grpc_target:
            grpc_target = "remote.buildbuddy.io"

        get_execution_rsp = call_rpc(
            args.base_url,
            api_key,
            "GetExecution",
            {
                "requestContext": {"groupId": args.group_id},
                "executionLookup": {"invocationId": invocation_id},
                "inlineExecuteResponse": True,
            },
        )
        executions = list(get_execution_rsp.get("execution", []) or [])
        if not executions:
            raise RuntimeError("GetExecution returned no executions for invocation.")
        selected = choose_execution(executions, args)

        if args.selection_json:
            with open(args.selection_json, "w", encoding="utf-8") as f:
                json.dump(selected, f, indent=2, sort_keys=True)
                f.write("\n")

        if args.verbose:
            eprint("Selected execution:")
            eprint("  " + summarize_execution(selected))

        action_digest = selected.get("actionDigest", {})
        action = download_proto_json(
            "Action",
            action_digest,
            instance_name=remote_instance,
            digest_function=digest_function,
            grpc_target=grpc_target,
            api_key=api_key,
            verbose=args.verbose,
        )
        command_digest = action.get("commandDigest")
        if not command_digest:
            raise RuntimeError("Action proto missing commandDigest.")
        command = download_proto_json(
            "Command",
            command_digest,
            instance_name=remote_instance,
            digest_function=digest_function,
            grpc_target=grpc_target,
            api_key=api_key,
            verbose=args.verbose,
        )

        env_items = [
            (e.get("name", ""), e.get("value", ""))
            for e in command.get("environmentVariables", [])
            if e.get("name", "") != ""
        ]
        set_env_items = [parse_key_value(x, "--set-action-env") for x in args.set_action_env]
        env_items = apply_overrides(env_items, args.remove_action_env, set_env_items)

        platform = action.get("platform")
        if not platform:
            platform = command.get("platform", {})
        prop_items = [
            (p.get("name", ""), p.get("value", ""))
            for p in platform.get("properties", [])
            if p.get("name", "") != ""
        ]
        set_exec_prop_items = [parse_key_value(x, "--set-exec-property") for x in args.set_exec_property]
        prop_items = apply_overrides(prop_items, args.remove_exec_property, set_exec_prop_items)

        pin_executor_id = args.pin_executor_id
        if args.pin_worker_host_id:
            pin_executor_id = resolve_executor_id_for_host(
                base_url=args.base_url,
                api_key=api_key,
                group_id=args.group_id,
                host_id=args.pin_worker_host_id,
            )
        elif args.pin_to_original_worker:
            worker_host_id = selected.get("executedActionMetadata", {}).get("worker", "")
            pin_executor_id = resolve_executor_id_for_host(
                base_url=args.base_url,
                api_key=api_key,
                group_id=args.group_id,
                host_id=worker_host_id,
            )

        if pin_executor_id:
            prop_items = apply_overrides(
                prop_items,
                [],
                [("debug-executor-id", pin_executor_id)],
            )

        output_paths = list(command.get("outputPaths", []) or [])
        if not output_paths:
            output_paths.extend(command.get("outputFiles", []) or [])
            output_paths.extend(command.get("outputDirectories", []) or [])

        cmd_args = list(args.arg_override) if args.arg_override else list(command.get("arguments", []) or [])
        if not cmd_args:
            raise RuntimeError("No command arguments found in Command proto and no --arg override provided.")

        invocation_id_for_command = invocation_id
        if args.new_invocation_id:
            invocation_id_for_command = str(uuid.uuid4())

        parts: list[str] = ["bb", "execute"]
        unquoted: set[int] = set()
        if args.api_key_in_command:
            parts.append(f"--remote_header=x-buildbuddy-api-key={api_key}")
        else:
            parts.append("--remote_header=x-buildbuddy-api-key=${BB_API_KEY?}")
            unquoted.add(len(parts) - 1)

        if remote_executor:
            parts.append(f"--remote_executor={remote_executor}")
        if digest_function in ("sha256", "blake3"):
            parts.append(f"--digest_function={digest_function}")
        if not args.omit_invocation_id:
            parts.append(f"--invocation_id={invocation_id_for_command}")
        if remote_instance:
            parts.append(f"--remote_instance_name={remote_instance}")

        timeout_seconds_raw = action.get("timeout", {}).get("seconds")
        if timeout_seconds_raw not in (None, "", "0", 0):
            timeout_seconds = int(timeout_seconds_raw)
            if timeout_seconds > 0:
                parts.append(f"--remote_timeout={timeout_seconds}s")

        input_root_digest = action.get("inputRootDigest", {})
        if input_root_digest.get("hash"):
            parts.append(f"--input_root_digest={digest_str(input_root_digest)}")

        for k, v in env_items:
            parts.append(f"--action_env={k}={v}")
        for k, v in prop_items:
            parts.append(f"--exec_properties={k}={v}")
        for p in output_paths:
            parts.append(f"--output_path={p}")

        parts.append("--")
        parts.extend(cmd_args)
        command_text = format_shell_command(parts, unquoted)

        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(command_text)
                f.write("\n")
        else:
            print(command_text)

        if args.verbose:
            eprint("Generated command successfully.")
        return 0
    except Exception as e:
        eprint(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
