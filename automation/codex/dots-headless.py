#!/usr/bin/env python3
"""Direct, GUI-free Dots executor enrollment and service supervision.

Enrollment uses the signed-in shared app-server's supported auth RPC and workspace
routing. The stock exec-server owns credential refresh and outbound Noise transport.
Only actual local skills are advertised: no desktop/browser/IPC capabilities.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
from pathlib import Path
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import uuid

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
CLIENT_NAME = "codex-headless-dots"
CLIENT_VERSION = "0.1.0"
REGISTRY = "https://codex-cloud-environments.chatgpt.com/api"

class RpcError(RuntimeError):
    pass

class SetupError(RuntimeError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def recv_until(sock: socket.socket, marker: bytes) -> bytes:
    data = bytearray()
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise RpcError("socket closed during WebSocket handshake")
        data.extend(chunk)
        if len(data) > 64 * 1024:
            raise RpcError("WebSocket handshake response was too large")
    return bytes(data)


def connect_websocket(socket_path: Path, timeout: float) -> socket.socket:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(str(socket_path))
    except OSError as exc:
        sock.close()
        raise RpcError(f"failed to connect to {socket_path}: {exc}") from exc

    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        "GET /rpc HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    ).encode("ascii")
    sock.sendall(request)
    response = recv_until(sock, b"\r\n\r\n").decode("iso-8859-1")
    header_block, _body = response.split("\r\n\r\n", 1)
    lines = header_block.split("\r\n")
    if not lines or " 101 " not in lines[0]:
        raise RpcError(f"WebSocket upgrade failed: {lines[0] if lines else response!r}")

    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()
    expected_accept = base64.b64encode(hashlib.sha1((key + GUID).encode("ascii")).digest()).decode(
        "ascii"
    )
    if headers.get("sec-websocket-accept") != expected_accept:
        raise RpcError("WebSocket upgrade returned an invalid Sec-WebSocket-Accept header")
    return sock


def send_frame(sock: socket.socket, opcode: int, payload: bytes = b"") -> None:
    first = 0x80 | opcode
    length = len(payload)
    if length < 126:
        header = bytes([first, 0x80 | length])
    elif length <= 0xFFFF:
        header = bytes([first, 0x80 | 126]) + struct.pack("!H", length)
    else:
        header = bytes([first, 0x80 | 127]) + struct.pack("!Q", length)
    mask = os.urandom(4)
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    sock.sendall(header + mask + masked)


def read_exact(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise RpcError("socket closed while reading WebSocket frame")
        data.extend(chunk)
    return bytes(data)


def read_text_frame(sock: socket.socket) -> str:
    fragments: list[bytes] = []
    while True:
        first, second = read_exact(sock, 2)
        fin = bool(first & 0x80)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", read_exact(sock, 2))[0]
        elif length == 127:
            length = struct.unpack("!Q", read_exact(sock, 8))[0]

        mask = read_exact(sock, 4) if masked else b""
        payload = read_exact(sock, length)
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))

        if opcode == 0x8:
            raise RpcError("app-server closed the WebSocket")
        if opcode == 0x9:
            send_frame(sock, 0xA, payload)
            continue
        if opcode == 0xA:
            continue
        if opcode in (0x1, 0x0):
            fragments.append(payload)
            if fin:
                return b"".join(fragments).decode("utf-8")
            continue
        if opcode == 0x2:
            continue
        raise RpcError(f"unexpected WebSocket opcode {opcode}")


def send_json(sock: socket.socket, message: dict[str, Any]) -> None:
    send_frame(sock, 0x1, json.dumps(message, separators=(",", ":")).encode("utf-8"))


def read_response(sock: socket.socket, request_id: int) -> dict[str, Any]:
    while True:
        message = json.loads(read_text_frame(sock))
        if message.get("id") != request_id:
            continue
        if "error" in message:
            raise RpcError("app-server RPC rejected the request")
        return message


def initialize(sock: socket.socket) -> None:
    send_json(
        sock,
        {
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": CLIENT_NAME,
                    "title": "Codex Remote Control Status",
                    "version": CLIENT_VERSION,
                },
                "capabilities": {"experimentalApi": True},
            },
        },
    )
    read_response(sock, 1)
    send_json(sock, {"method": "initialized"})



def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def state_dir() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "codex-dots"


def write_private(path: Path, value: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.parent.stat().st_uid != os.getuid():
        raise SetupError("state directory is not owned by this user")
    os.chmod(path.parent, 0o700)
    fd, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, sort_keys=True)
            stream.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_private(path: Path) -> Any:
    info = path.lstat()
    if path.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise SetupError("state file must be a private user-owned regular file")
    if not path.is_file():
        raise SetupError("state file is not a regular file")
    return json.loads(path.read_text())


def rpc(method: str, params: dict[str, Any]) -> Any:
    sock = connect_websocket(codex_home() / "app-server-control/app-server-control.sock", 30)
    try:
        initialize(sock)
        send_json(sock, {"id": 2, "method": method, "params": params})
        return read_response(sock, 2)["result"]
    finally:
        sock.close()


def principal(token: str) -> dict[str, str]:
    try:
        claim = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "===")).get(
            "https://api.openai.com/auth", {}
        )
        account = claim.get("chatgpt_account_id") or claim.get("account_id")
        user = claim.get("chatgpt_user_id") or claim.get("user_id")
        if not isinstance(account, str) or not account or not isinstance(user, str) or not user:
            raise ValueError()
        return {"accountId": account, "userId": user}
    except (ValueError, IndexError, TypeError, binascii.Error, UnicodeDecodeError):
        raise SetupError("ChatGPT credential lacks a complete account and user identity") from None


def authentication(refresh: bool = False) -> tuple[str, dict[str, str], dict[str, Any]]:
    account = rpc("account/read", {"refreshToken": refresh})
    auth = rpc("getAuthStatus", {"includeToken": True, "refreshToken": False})
    if (account.get("account") or {}).get("type") != "chatgpt" or auth.get("authMethod") != "chatgpt":
        raise SetupError("a managed ChatGPT login is required")
    token = auth.get("authToken")
    if not isinstance(token, str) or not token:
        raise SetupError("ChatGPT authentication is unavailable")
    owner = principal(token)
    routing = account.get("workspaceRouting")
    if not routing or routing.get("chatgptAccountId") != owner["accountId"]:
        raise SetupError("workspace routing does not match the signed-in account")
    # Fail closed rather than bypass residency or enterprise routing policy.
    if routing.get("backendOrigin") != "https://chatgpt.com" or routing.get("accountRoutingOverride") != "NO_CONSTRAINT":
        raise SetupError("this helper does not support the account's workspace routing policy")
    return token, owner, routing


def request(method: str, path: str, body: Any = None, *, registry: bool = False,
            expected: dict[str, str] | None = None) -> Any:
    if not path.startswith("/") or path.startswith("//"):
        raise SetupError("invalid API path")
    for refresh in (False, True):
        token, owner, routing = authentication(refresh)
        if expected is not None and owner != expected:
            raise SetupError("the signed-in identity changed; refusing executor access")
        base = REGISTRY if registry else routing["backendOrigin"] + "/backend-api"
        headers = {
            "Authorization": "Bearer " + token,
            "ChatGPT-Account-Id": owner["accountId"],
            "User-Agent": CLIENT_NAME + "/" + CLIENT_VERSION,
            "originator": "codex_headless_dots",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(base + path, headers=headers, method=method,
            data=None if body is None else json.dumps(body).encode())
        try:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
                data = response.read(2 * 1024 * 1024)
                return json.loads(data) if data else None
        except urllib.error.HTTPError as exc:
            if exc.code == 401 and not refresh:
                continue
            # Never print auth payloads or arbitrary response bodies.
            raise SetupError(f"{method} {path.split('?')[0]} returned HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            raise SetupError("backend request failed or returned invalid JSON") from None
    raise SetupError("authentication refresh did not resolve the request")


def identity() -> str:
    path = state_dir() / "installation-id"
    if not path.exists():
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(str(uuid.uuid4()) + "\n")
        except FileExistsError:
            pass
    info = path.lstat()
    if path.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise SetupError("installation identity is not private and user-owned")
    try:
        return str(uuid.UUID(path.read_text().strip()))
    except ValueError:
        raise SetupError("installation identity is invalid") from None


def enroll() -> dict[str, Any]:
    _, owner, _ = authentication()
    path = state_dir() / "executor.json"
    if path.exists() and read_private(path)["owner"] != owner:
        raise SetupError("executor belongs to another login; stop before re-enrollment")
    skills = codex_home() / "skills"
    roots = [{"id": "codex-home-skills", "path": str(skills)}] if skills.is_dir() else []
    result = request("POST", "/flora/cca/executor", {
        "displayName": socket.gethostname()[:80] + " (headless)",
        "installation_id": identity(),
        "selected_capability_roots": roots,
    }, expected=owner)
    environment = result.get("executor_id") if isinstance(result, dict) else None
    if not isinstance(environment, str) or not environment.strip():
        raise SetupError("executor enrollment returned no environment identity")
    state = {"version": 1, "owner": owner, "environmentId": environment,
             "installationId": identity(), "capabilityRoots": roots}
    write_private(path, state)
    return state


def registry_status(state: dict[str, Any]) -> Any:
    environment = urllib.parse.quote(state["environmentId"], safe="")
    result = request("GET", f"/cloud/environment/{environment}/status",
                     registry=True, expected=state["owner"])
    if result.get("environment_id") != state["environmentId"]:
        raise SetupError("registry status returned a different executor")
    return {"registryStatus": result.get("status")}


def dots(state: dict[str, Any]) -> list[dict[str, Any]]:
    items, cursor = [], None
    for _ in range(100):
        query = {"limit": 25, "include_room_preview": "false"}
        if cursor:
            query["cursor"] = cursor
        result = request("GET", "/tbo?" + urllib.parse.urlencode(query), expected=state["owner"])
        items.extend(result["items"])
        cursor = result.get("cursor")
        if not cursor:
            return items
    raise SetupError("dot catalog exceeded pagination limit")


def connect(state: dict[str, Any]) -> dict[str, Any]:
    candidates = [item for item in dots(state)
                  if item.get("aeon_kind") == "orbit" and item.get("status") == "active"
                  and item.get("scope") == "personal"
                  and item.get("service_account_account_user_id") is None
                  and not any(item.get(key) for key in ("is_paused", "is_admin_paused", "isSafetyFlagged", "safety_flag"))]
    if len(candidates) != 1:
        raise SetupError("cannot identify one unambiguous active personal dot")
    dot = candidates[0]
    thread = dot.get("active_root_thread_id")
    if not thread:
        raise SetupError("personal dot has no active root thread")
    base = "/tbo/" + urllib.parse.quote(dot["id"], safe="") + "/computers"
    query = "?" + urllib.parse.urlencode({"expected_thread_id": thread})
    before = request("GET", base + query, expected=state["owner"])
    if before.get("thread_id") != thread:
        raise SetupError("dot thread changed before attachment")
    # Never use connect-and-replace: preserving existing attached machines is required.
    request("POST", base + "/" + urllib.parse.quote(state["environmentId"], safe="") + "/connect" + query,
            expected=state["owner"])
    after = request("GET", base + query, expected=state["owner"])
    if after.get("thread_id") != thread or not any(
        computer.get("environment_id") == state["environmentId"] and computer.get("is_attached")
        for computer in after.get("computers", [])
    ):
        raise SetupError("backend did not confirm executor attachment")
    write_private(state_dir() / "attachment.json", {"dotId": dot["id"], "threadId": thread,
                  "previousComputers": before, "environmentId": state["environmentId"]})
    return {"attached": True}


def run() -> int:
    state = enroll()
    env = dict(os.environ)
    env.update({"LOG_FORMAT": "json", "RUST_LOG": "warn,codex_exec_server::remote=info"})
    # Managed ChatGPT auth in the stock executor reloads/refreshes credentials and
    # pins account+user. No bearer appears in argv, environment or this state.
    child = subprocess.Popen([
        "/usr/bin/codex", "-c", 'forced_login_method="chatgpt"',
        "exec-server", "--concurrent-requests", "32", "--remote", REGISTRY,
        "--environment-id", state["environmentId"],
    ], cwd=Path.home(), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    stopping = False
    def stop(signum, frame):
        nonlocal stopping
        stopping = True
        try:
            child.terminate()
        except ProcessLookupError:
            pass
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    # Only publish whitelisted structured diagnostics. Native error URLs and
    # arbitrary error payloads may contain transport credentials.
    for line in child.stderr:
        try:
            entry = json.loads(line)
            fields = entry.get("fields", {})
            if entry.get("target") != "codex_exec_server::remote" or "noise_event" not in fields:
                continue
            safe = {key: value for key, value in fields.items() if key in (
                "noise_event", "noise_outcome", "noise_reason", "error_kind", "rejection_reason")
                and isinstance(value, str) and re.fullmatch(r"[a-z0-9_]{1,80}", value)}
            if "noise_event" not in safe:
                continue
            for key in ("http_status", "connection_attempt"):
                value = fields.get(key)
                if isinstance(value, int) and 0 < value < 2**53:
                    safe[key] = value
            write_private(state_dir() / "transport.json", {"time": time.time(), **safe})
            print(json.dumps(safe), flush=True)
        except (ValueError, TypeError):
            # Current native builds use tracing text even with LOG_FORMAT=json.
            if "codex_exec_server::remote" not in line:
                continue
            line = re.sub(r"\x1b\[[0-9;]*m", "", line)
            safe = {}
            for key in ("noise_event", "noise_outcome", "noise_reason", "error_kind", "rejection_reason"):
                match = re.search(r"\b" + key + r'="([a-z0-9_]+)"', line)
                if match:
                    safe[key] = match.group(1)
            if "noise_event" not in safe:
                continue
            write_private(state_dir() / "transport.json", {"time": time.time(), **safe})
            print(json.dumps(safe), flush=True)
    code = child.wait()
    write_private(state_dir() / "transport.json", {"time": time.time(), "exited": code})
    print(json.dumps({"executorExited": code}), flush=True)
    return 0 if stopping else code or 1


def main() -> int:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("enroll", "run", "status", "dots", "connect"))
    args = parser.parse_args()
    try:
        if args.command == "run":
            return run()
        if args.command == "enroll":
            state = enroll()
            result = {"enrolled": True, "capabilityRootCount": len(state["capabilityRoots"])}
        else:
            state = read_private(state_dir() / "executor.json")
            if args.command == "status":
                result = registry_status(state)
            elif args.command == "connect":
                result = connect(state)
            else:
                result = {"dotCount": len(dots(state))}
        print(json.dumps(result, sort_keys=True))
        return 0
    except (SetupError, RpcError, OSError, KeyError, TypeError) as exc:
        # System errors can contain paths, but no response bodies or credentials.
        print(json.dumps({"error": str(exc) if isinstance(exc, (SetupError, RpcError)) else "local executor operation failed"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
