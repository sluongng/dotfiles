#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import os
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VERSION = "0.2.0"
DEFAULT_BASE_URL = "https://public-api.etoro.com"
DEFAULT_FIELDS = "instrumentId,displayname,symbol,instrumentType,exchangeID,isOpen,isCurrentlyTradable"
SECRET_ENV_NAMES = ("ETORO_API_KEY", "ETORO_USER_KEY")
WRITE_WARNING = "Trading write request. Dry-run sends no network request; execution can place or cancel real orders."


class CliError(Exception):
    def __init__(self, error_type: str, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.status = status


class ApiError(CliError):
    def __init__(self, status: int, body: Any, message: str) -> None:
        super().__init__("api_error", message, status=status)
        self.body = body


@dataclass(frozen=True)
class AuthConfig:
    base_url: str
    api_key: str | None
    user_key: str | None
    config_path: Path
    api_key_source: str
    user_key_source: str
    base_url_source: str
    config_mode: str | None
    config_permissions_ok: bool | None

    @property
    def auth_available(self) -> bool:
        return bool(self.api_key and self.user_key)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CliError as exc:
        emit_error(args, exc)
        return 1
    except KeyboardInterrupt:
        emit_error(args, CliError("interrupted", "Interrupted"))
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="etoro-api",
        description="Credential-safe CLI for the official eToro Public API.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check config, auth source, and API reachability.")
    doctor.add_argument("--skip-network", action="store_true", help="Do not call the eToro API host.")
    doctor.set_defaults(func=cmd_doctor)

    init = subparsers.add_parser("init", help="Interactively store API credentials in local config.")
    init.add_argument("--from-env", action="store_true", help="Write ETORO_API_KEY/ETORO_USER_KEY from the current environment.")
    init.add_argument("--force", action="store_true", help="Overwrite an existing config file.")
    init.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"API base URL. Default: {DEFAULT_BASE_URL}")
    init.set_defaults(func=cmd_init)

    me = subparsers.add_parser("me", help="Get authenticated user identity.")
    add_out(me)
    me.set_defaults(func=lambda args: get_endpoint(args, "/api/v1/me"))

    portfolio = subparsers.add_parser("portfolio", help="Get real or demo portfolio details.")
    add_account(portfolio)
    add_out(portfolio)
    portfolio.set_defaults(func=cmd_portfolio)

    pnl = subparsers.add_parser("pnl", help="Get real or demo account PnL details.")
    add_account(pnl)
    add_out(pnl)
    pnl.set_defaults(func=cmd_pnl)

    history = subparsers.add_parser("trade-history", help="List real-account trading history.")
    history.add_argument("--min-date", required=True, help="Start date, YYYY-MM-DD.")
    history.add_argument("--page", type=int, help="Page number.")
    history.add_argument("--page-size", type=int, help="Trades per page.")
    add_out(history)
    history.set_defaults(func=cmd_trade_history)

    search = subparsers.add_parser("instrument-search", help="Search eToro instruments.")
    search.add_argument("--search-text", help="Text to search for.")
    search.add_argument("--limit", type=int, default=20, help="Result count. Default: 20.")
    search.add_argument("--page", type=int, default=1, help="Page number. Default: 1.")
    search.add_argument("--fields", default=DEFAULT_FIELDS, help="Comma-separated response fields.")
    search.add_argument("--sort", help="Sort expression, for example 'popularityUniques7Day desc'.")
    add_out(search)
    search.set_defaults(func=cmd_instrument_search)

    instruments = subparsers.add_parser("instruments", help="Retrieve instrument metadata.")
    instruments.add_argument("--instrument-id", action="append", help="Instrument ID. Can be repeated or comma-separated.")
    instruments.add_argument("--exchange-id", action="append", help="Exchange ID. Can be repeated or comma-separated.")
    instruments.add_argument("--stock-industry-id", action="append", help="Stock industry ID. Can be repeated or comma-separated.")
    instruments.add_argument("--instrument-type-id", action="append", help="Instrument type ID. Can be repeated or comma-separated.")
    add_out(instruments)
    instruments.set_defaults(func=cmd_instruments)

    rates = subparsers.add_parser("rates", help="Retrieve current rates for up to 100 instrument IDs.")
    rates.add_argument("instrument_ids", nargs="+", help="Instrument IDs, separated by spaces or commas.")
    add_out(rates)
    rates.set_defaults(func=cmd_rates)

    candles = subparsers.add_parser("candles", help="Retrieve OHLCV candles for one instrument.")
    candles.add_argument("instrument_id", type=int, help="eToro instrument ID.")
    candles.add_argument("--direction", choices=("asc", "desc"), default="desc", help="Sort direction. Default: desc.")
    candles.add_argument("--interval", default="OneDay", help="Candle interval, for example OneDay.")
    candles.add_argument("--count", type=int, default=100, help="Number of candles, max 1000. Default: 100.")
    add_out(candles)
    candles.set_defaults(func=cmd_candles)

    snapshot = subparsers.add_parser("snapshot", help="Write identity, portfolio, PnL, and optional trade history to files.")
    add_account(snapshot)
    snapshot.add_argument("--trade-history-min-date", help="Also fetch trade history from this date.")
    snapshot.add_argument("--out", required=True, type=Path, help="Output directory for JSON files.")
    snapshot.set_defaults(func=cmd_snapshot)

    trade = subparsers.add_parser(
        "trade",
        help="Prepare or execute trading write requests with explicit confirmation gates.",
    )
    trade_subparsers = trade.add_subparsers(dest="trade_command", required=True)

    close_position = trade_subparsers.add_parser(
        "close-position",
        help="Create a market order to close all or part of an existing position.",
    )
    add_write_account(close_position)
    close_position.add_argument("--position-id", required=True, type=int, help="Position ID to close.")
    close_position.add_argument(
        "--instrument-id",
        required=True,
        type=int,
        help="eToro instrument ID for the position.",
    )
    close_position.add_argument(
        "--units-to-deduct",
        type=float,
        help="Units to close. Omit to close the full position.",
    )
    add_write_controls(close_position)
    add_out(close_position)
    close_position.set_defaults(func=cmd_trade_close_position)

    open_market = trade_subparsers.add_parser(
        "open-market",
        help="Create a market order to open a long or short position.",
    )
    add_write_account(open_market)
    open_market.add_argument("--instrument-id", required=True, type=int, help="eToro instrument ID.")
    open_market.add_argument(
        "--side",
        required=True,
        choices=("long", "short"),
        help="long maps to IsBuy=true; short opens a short position and does not close an existing long.",
    )
    open_market.add_argument("--leverage", type=int, default=1, help="Leverage multiplier. Default: 1.")
    amount_group = open_market.add_mutually_exclusive_group(required=True)
    amount_group.add_argument("--amount", type=float, help="Cash amount in USD to invest.")
    amount_group.add_argument("--units", type=float, help="Units to trade.")
    add_risk_controls(open_market)
    add_write_controls(open_market)
    add_out(open_market)
    open_market.set_defaults(func=cmd_trade_open_market)

    cancel_order = trade_subparsers.add_parser(
        "cancel-order",
        help="Cancel a pending market-open, market-close, or market-if-touched order.",
    )
    add_write_account(cancel_order)
    cancel_order.add_argument("--order-id", required=True, type=int, help="Order ID to cancel.")
    cancel_order.add_argument(
        "--kind",
        required=True,
        choices=("open", "close", "limit"),
        help="Pending order type to cancel.",
    )
    add_write_controls(cancel_order)
    add_out(cancel_order)
    cancel_order.set_defaults(func=cmd_trade_cancel_order)

    order_info = trade_subparsers.add_parser("order-info", help="Get order and position details.")
    add_write_account(order_info)
    order_info.add_argument("--order-id", required=True, type=int, help="Order ID to inspect.")
    add_out(order_info)
    order_info.set_defaults(func=cmd_trade_order_info)

    request = subparsers.add_parser("request", help="Read-only raw API escape hatch.")
    request.add_argument("method", choices=("get", "head"), help="HTTP method. Only GET and HEAD are supported.")
    request.add_argument("path", help="API path, for example /api/v1/me.")
    request.add_argument("--param", action="append", default=[], help="Query parameter as key=value. Can be repeated.")
    add_out(request)
    request.set_defaults(func=cmd_request)

    return parser


def add_account(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--account", choices=("real", "demo"), default="real", help="Account environment. Default: real.")


def add_write_account(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--account",
        required=True,
        choices=("real", "demo"),
        help="Account environment. Required for write-capable commands.",
    )


def add_out(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out", type=Path, help="Write full API response to this JSON file and print only metadata.")


def add_write_controls(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Send the write request. Without this flag the command only prints a dry-run ticket.",
    )
    parser.add_argument(
        "--confirm",
        help="Exact confirmation token from the dry-run ticket. Required with --execute.",
    )


def add_risk_controls(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--stop-loss-rate", type=float, help="Stop-loss trigger price.")
    parser.add_argument("--take-profit-rate", type=float, help="Take-profit trigger price.")
    parser.add_argument(
        "--trailing-stop-loss",
        action="store_true",
        help="Enable trailing stop loss using the stop-loss rate.",
    )
    parser.add_argument("--no-stop-loss", action="store_true", help="Open with no stop-loss.")
    parser.add_argument("--no-take-profit", action="store_true", help="Open with no take-profit.")


def cmd_init(args: argparse.Namespace) -> int:
    config_path = get_config_path()
    if config_path.exists() and not args.force:
        raise CliError("config_exists", f"{config_path} already exists; use --force to overwrite")

    if args.from_env:
        api_key = os.environ.get("ETORO_API_KEY")
        user_key = os.environ.get("ETORO_USER_KEY")
        if not api_key or not user_key:
            raise CliError("missing_auth", "ETORO_API_KEY and ETORO_USER_KEY must both be set")
    else:
        if not sys.stdin.isatty():
            raise CliError("not_interactive", "run etoro-api init in a terminal, or use --from-env")
        print("Paste eToro credentials. Input is hidden and values will not be printed.", file=sys.stderr)
        api_key = getpass.getpass("Public API key: ")
        user_key = getpass.getpass("User key: ")

    config = {
        "base_url": args.base_url.rstrip("/"),
        "api_key": api_key,
        "user_key": user_key,
    }
    write_config(config_path, config)
    emit(
        args,
        {
            "ok": True,
            "config_path": str(config_path),
            "mode": "0600",
            "message": "Credentials stored without printing key values.",
        },
        human=f"Wrote {config_path} with mode 0600",
    )
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = load_auth_config()
    result: dict[str, Any] = {
        "ok": True,
        "version": VERSION,
        "base_url": cfg.base_url,
        "config_path": str(cfg.config_path),
        "auth": {
            "available": cfg.auth_available,
            "api_key_source": cfg.api_key_source,
            "user_key_source": cfg.user_key_source,
            "base_url_source": cfg.base_url_source,
            "missing": missing_auth_fields(cfg),
        },
        "config_file": {
            "exists": cfg.config_path.exists(),
            "mode": cfg.config_mode,
            "permissions_ok": cfg.config_permissions_ok,
        },
    }

    if not args.skip_network:
        result["network"] = check_network(cfg)
    else:
        result["network"] = {"skipped": True}

    emit(args, result, human=doctor_human(result))
    return 0


def cmd_portfolio(args: argparse.Namespace) -> int:
    path = "/api/v1/trading/info/portfolio"
    if args.account == "demo":
        path = "/api/v1/trading/info/demo/portfolio"
    return get_endpoint(args, path)


def cmd_pnl(args: argparse.Namespace) -> int:
    path = "/api/v1/trading/info/real/pnl"
    if args.account == "demo":
        path = "/api/v1/trading/info/demo/pnl"
    return get_endpoint(args, path)


def cmd_trade_history(args: argparse.Namespace) -> int:
    params: dict[str, Any] = {"minDate": args.min_date}
    if args.page is not None:
        params["page"] = args.page
    if args.page_size is not None:
        params["pageSize"] = args.page_size
    return get_endpoint(args, "/api/v1/trading/info/trade/history", params=params)


def cmd_instrument_search(args: argparse.Namespace) -> int:
    params: dict[str, Any] = {
        "pageSize": args.limit,
        "pageNumber": args.page,
        "fields": args.fields,
    }
    if args.search_text:
        params["searchText"] = args.search_text
    if args.sort:
        params["sort"] = args.sort
    return get_endpoint(args, "/api/v1/market-data/search", params=params)


def cmd_instruments(args: argparse.Namespace) -> int:
    params: dict[str, Any] = {}
    add_csv_param(params, "instrumentIds", args.instrument_id)
    add_csv_param(params, "exchangeIds", args.exchange_id)
    add_csv_param(params, "stocksIndustryIds", args.stock_industry_id)
    add_csv_param(params, "instrumentTypeIds", args.instrument_type_id)
    return get_endpoint(args, "/api/v1/market-data/instruments", params=params)


def cmd_rates(args: argparse.Namespace) -> int:
    ids = split_csv(args.instrument_ids)
    if len(ids) > 100:
        raise CliError("invalid_input", "rates accepts at most 100 instrument IDs")
    return get_endpoint(args, "/api/v1/market-data/instruments/rates", params={"instrumentIds": ",".join(ids)})


def cmd_candles(args: argparse.Namespace) -> int:
    if args.count > 1000:
        raise CliError("invalid_input", "candles --count must be <= 1000")
    path = (
        f"/api/v1/market-data/instruments/{args.instrument_id}"
        f"/history/candles/{args.direction}/{args.interval}/{args.count}"
    )
    return get_endpoint(args, path)


def cmd_snapshot(args: argparse.Namespace) -> int:
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    endpoints = {
        "me": ("/api/v1/me", None),
        "portfolio": (
            "/api/v1/trading/info/demo/portfolio"
            if args.account == "demo"
            else "/api/v1/trading/info/portfolio",
            None,
        ),
        "pnl": (
            "/api/v1/trading/info/demo/pnl"
            if args.account == "demo"
            else "/api/v1/trading/info/real/pnl",
            None,
        ),
    }
    if args.trade_history_min_date:
        endpoints["trade-history"] = (
            "/api/v1/trading/info/trade/history",
            {"minDate": args.trade_history_min_date},
        )

    written = []
    for name, (path, params) in endpoints.items():
        response = request_json("GET", path, params=params)
        target = out_dir / f"{name}.json"
        byte_count = write_json_file(target, response["body"])
        written.append(
            {
                "name": name,
                "path": str(target),
                "status": response["status"],
                "bytes": byte_count,
            }
        )

    metadata = {
        "ok": True,
        "account": args.account,
        "base_url": load_auth_config().base_url,
        "files": written,
    }
    write_json_file(out_dir / "metadata.json", metadata)
    emit(args, metadata, human=f"Wrote {len(written)} eToro snapshot files to {out_dir}")
    return 0


def cmd_trade_close_position(args: argparse.Namespace) -> int:
    require_positive_int(args.position_id, "position-id")
    require_positive_int(args.instrument_id, "instrument-id")
    if args.units_to_deduct is not None:
        require_positive_number(args.units_to_deduct, "units-to-deduct")

    path = trading_execution_path(
        args.account,
        real=f"/api/v1/trading/execution/market-close-orders/positions/{args.position_id}",
        demo=f"/api/v1/trading/execution/demo/market-close-orders/positions/{args.position_id}",
    )
    instrument_key = "InstrumentID" if args.account == "demo" else "InstrumentId"
    body: dict[str, Any] = {instrument_key: args.instrument_id}
    if args.units_to_deduct is not None:
        body["UnitsToDeduct"] = args.units_to_deduct

    token = (
        f"execute-close-{args.account}-position-{args.position_id}"
        f"-instrument-{args.instrument_id}"
    )
    return execute_or_dry_run(
        args,
        action="close-position",
        method="POST",
        path=path,
        body=body,
        confirm_token=token,
    )


def cmd_trade_open_market(args: argparse.Namespace) -> int:
    require_positive_int(args.instrument_id, "instrument-id")
    require_positive_int(args.leverage, "leverage")
    validate_risk_controls(args)

    body: dict[str, Any] = {
        "InstrumentID": args.instrument_id,
        "IsBuy": args.side == "long",
        "Leverage": args.leverage,
    }
    if args.amount is not None:
        require_positive_number(args.amount, "amount")
        path_suffix = "by-amount"
        body["Amount"] = args.amount
    else:
        require_positive_number(args.units, "units")
        path_suffix = "by-units"
        body["AmountInUnits"] = args.units

    add_optional_trade_fields(args, body)
    path = trading_execution_path(
        args.account,
        real=f"/api/v1/trading/execution/market-open-orders/{path_suffix}",
        demo=f"/api/v1/trading/execution/demo/market-open-orders/{path_suffix}",
    )
    token = f"execute-open-{args.account}-{args.side}-instrument-{args.instrument_id}"
    return execute_or_dry_run(
        args,
        action="open-market",
        method="POST",
        path=path,
        body=body,
        confirm_token=token,
    )


def cmd_trade_cancel_order(args: argparse.Namespace) -> int:
    require_positive_int(args.order_id, "order-id")
    order_paths = {
        "open": "market-open-orders",
        "close": "market-close-orders",
        "limit": "limit-orders",
    }
    segment = order_paths[args.kind]
    path = trading_execution_path(
        args.account,
        real=f"/api/v1/trading/execution/{segment}/{args.order_id}",
        demo=f"/api/v1/trading/execution/demo/{segment}/{args.order_id}",
    )
    token = f"execute-cancel-{args.account}-{args.kind}-order-{args.order_id}"
    return execute_or_dry_run(
        args,
        action="cancel-order",
        method="DELETE",
        path=path,
        body=None,
        confirm_token=token,
    )


def cmd_trade_order_info(args: argparse.Namespace) -> int:
    require_positive_int(args.order_id, "order-id")
    path = (
        f"/api/v1/trading/info/demo/orders/{args.order_id}"
        if args.account == "demo"
        else f"/api/v1/trading/info/real/orders/{args.order_id}"
    )
    return get_endpoint(args, path)


def cmd_request(args: argparse.Namespace) -> int:
    params = parse_params(args.param)
    return get_endpoint(args, args.path, method=args.method.upper(), params=params)


def get_endpoint(
    args: argparse.Namespace,
    path: str,
    *,
    method: str = "GET",
    params: dict[str, Any] | None = None,
) -> int:
    response = request_json(method, path, params=params)
    if args.out:
        byte_count = write_json_file(args.out, response["body"])
        emit(
            args,
            {"ok": True, "status": response["status"], "path": str(args.out), "bytes": byte_count},
            human=f"Wrote {args.out}",
        )
    else:
        emit(args, response["body"])
    return 0


def request_json(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if method not in {"GET", "HEAD", "POST", "DELETE"}:
        raise CliError("invalid_method", "only GET, HEAD, POST, and DELETE are supported")

    cfg = load_auth_config()
    if not cfg.auth_available:
        missing = ", ".join(missing_auth_fields(cfg))
        raise CliError("missing_auth", f"missing credentials: {missing}")

    url = build_url(cfg.base_url, path, params)
    data = None
    headers = auth_headers(cfg)
    if json_body is not None:
        data = json.dumps(json_body, separators=(",", ":")).encode("utf-8")
        headers["content-type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            body = None if method == "HEAD" else parse_body(raw, response.headers.get("content-type", ""))
            return {"status": response.status, "body": body}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        body = parse_body(raw, exc.headers.get("content-type", ""))
        message = api_error_message(body, exc)
        raise ApiError(exc.code, body, message) from exc
    except urllib.error.URLError as exc:
        raise CliError("network_error", redact(str(exc))) from exc


def check_network(cfg: AuthConfig) -> dict[str, Any]:
    headers = {"x-request-id": str(uuid.uuid4()), "user-agent": f"etoro-api-cli/{VERSION}"}
    if cfg.auth_available:
        headers.update(auth_headers(cfg))
    request = urllib.request.Request(build_url(cfg.base_url, "/api/v1/me", None), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response.read()
            return {
                "reachable": True,
                "status": response.status,
                "authenticated": cfg.auth_available and response.status == 200,
            }
    except urllib.error.HTTPError as exc:
        body = parse_body(exc.read(), exc.headers.get("content-type", ""))
        expected_without_auth = not cfg.auth_available and exc.code in {401, 422}
        return {
            "reachable": True,
            "status": exc.code,
            "authenticated": False,
            "expected_without_auth": expected_without_auth,
            "error_code": body.get("errorCode") if isinstance(body, dict) else None,
        }
    except urllib.error.URLError as exc:
        return {"reachable": False, "error": redact(str(exc))}


def load_auth_config() -> AuthConfig:
    config_path = get_config_path()
    file_config: dict[str, Any] = {}
    config_mode = None
    config_permissions_ok = None
    if config_path.exists():
        mode = stat.S_IMODE(config_path.stat().st_mode)
        config_mode = oct(mode)
        config_permissions_ok = (mode & 0o077) == 0
        try:
            file_config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CliError("invalid_config", f"{config_path} is not valid JSON") from exc

    base_url = os.environ.get("ETORO_BASE_URL") or file_config.get("base_url") or DEFAULT_BASE_URL
    api_key = os.environ.get("ETORO_API_KEY") or file_config.get("api_key")
    user_key = os.environ.get("ETORO_USER_KEY") or file_config.get("user_key")
    return AuthConfig(
        base_url=str(base_url).rstrip("/"),
        api_key=api_key,
        user_key=user_key,
        config_path=config_path,
        api_key_source=source_name("ETORO_API_KEY", "api_key", file_config),
        user_key_source=source_name("ETORO_USER_KEY", "user_key", file_config),
        base_url_source=source_name("ETORO_BASE_URL", "base_url", file_config, default="default"),
        config_mode=config_mode,
        config_permissions_ok=config_permissions_ok,
    )


def source_name(env_name: str, config_key: str, config: dict[str, Any], *, default: str = "missing") -> str:
    if os.environ.get(env_name):
        return "env"
    if config.get(config_key):
        return "config"
    return default


def missing_auth_fields(cfg: AuthConfig) -> list[str]:
    missing = []
    if not cfg.api_key:
        missing.append("ETORO_API_KEY")
    if not cfg.user_key:
        missing.append("ETORO_USER_KEY")
    return missing


def get_config_path() -> Path:
    custom = os.environ.get("ETORO_CONFIG")
    if custom:
        return Path(custom).expanduser()
    return Path.home() / ".config" / "etoro-api" / "config.json"


def write_config(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(config, indent=2, sort_keys=True) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(payload)
    os.chmod(path, 0o600)


def auth_headers(cfg: AuthConfig) -> dict[str, str]:
    return {
        "x-request-id": str(uuid.uuid4()),
        "x-api-key": cfg.api_key or "",
        "x-user-key": cfg.user_key or "",
        "accept": "application/json",
        "user-agent": f"etoro-api-cli/{VERSION}",
    }


def build_url(base_url: str, path: str, params: dict[str, Any] | None) -> str:
    if not path.startswith("/"):
        raise CliError("invalid_path", "path must start with /")
    url = base_url.rstrip("/") + path
    if params:
        clean = {key: value for key, value in params.items() if value not in (None, "", [])}
        if clean:
            url += "?" + urllib.parse.urlencode(clean, doseq=True)
    return url


def parse_body(raw: bytes, content_type: str) -> Any:
    if not raw:
        return None
    text = raw.decode("utf-8", "replace")
    if "json" in content_type.lower() or text[:1] in ("{", "["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text


def api_error_message(body: Any, exc: urllib.error.HTTPError) -> str:
    if isinstance(body, dict):
        return redact(str(body.get("errorMessage") or body.get("message") or exc.reason))
    return redact(str(exc.reason))


def parse_params(values: list[str]) -> dict[str, str]:
    params = {}
    for value in values:
        if "=" not in value:
            raise CliError("invalid_input", f"--param must use key=value: {value}")
        key, param_value = value.split("=", 1)
        if not key:
            raise CliError("invalid_input", f"--param must use key=value: {value}")
        params[key] = param_value
    return params


def add_csv_param(params: dict[str, Any], name: str, values: list[str] | None) -> None:
    ids = split_csv(values or [])
    if ids:
        params[name] = ",".join(ids)


def split_csv(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        for item in value.split(","):
            item = item.strip()
            if item:
                result.append(item)
    return result


def write_json_file(path: Path, data: Any) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
    return len(payload.encode("utf-8"))


def execute_or_dry_run(
    args: argparse.Namespace,
    *,
    action: str,
    method: str,
    path: str,
    body: dict[str, Any] | None,
    confirm_token: str,
) -> int:
    ticket: dict[str, Any] = {
        "ok": True,
        "action": action,
        "account": args.account,
        "dry_run": True,
        "method": method,
        "path": path,
        "body": body,
        "execution": {
            "execute_flag": "--execute",
            "confirm_flag": f"--confirm {confirm_token}",
            "confirm_token": confirm_token,
        },
        "warning": WRITE_WARNING,
    }
    if not args.execute:
        emit_maybe_out(args, ticket, human=f"Dry-run only. To execute, add --execute --confirm {confirm_token}")
        return 0

    if args.confirm != confirm_token:
        raise CliError(
            "confirmation_required",
            f"refusing write; rerun with --confirm {confirm_token}",
        )

    response = request_json(method, path, json_body=body)
    result = {
        "ok": True,
        "executed": True,
        "action": action,
        "account": args.account,
        "method": method,
        "path": path,
        "status": response["status"],
        "body": response["body"],
    }
    emit_maybe_out(args, result, human=f"Executed {action}; status {response['status']}")
    return 0


def emit_maybe_out(args: argparse.Namespace, payload: dict[str, Any], *, human: str) -> None:
    if args.out:
        byte_count = write_json_file(args.out, payload)
        emit(
            args,
            {"ok": True, "path": str(args.out), "bytes": byte_count},
            human=f"Wrote {args.out}",
        )
    else:
        emit(args, payload, human=human)


def trading_execution_path(account: str, *, real: str, demo: str) -> str:
    return demo if account == "demo" else real


def add_optional_trade_fields(args: argparse.Namespace, body: dict[str, Any]) -> None:
    if args.stop_loss_rate is not None:
        body["StopLossRate"] = args.stop_loss_rate
    if args.take_profit_rate is not None:
        body["TakeProfitRate"] = args.take_profit_rate
    if args.trailing_stop_loss:
        body["IsTslEnabled"] = True
    if args.no_stop_loss:
        body["IsNoStopLoss"] = True
    if args.no_take_profit:
        body["IsNoTakeProfit"] = True


def validate_risk_controls(args: argparse.Namespace) -> None:
    if args.stop_loss_rate is not None and args.no_stop_loss:
        raise CliError("invalid_input", "use either --stop-loss-rate or --no-stop-loss, not both")
    if args.take_profit_rate is not None and args.no_take_profit:
        raise CliError("invalid_input", "use either --take-profit-rate or --no-take-profit, not both")
    if args.trailing_stop_loss and args.stop_loss_rate is None:
        raise CliError("invalid_input", "--trailing-stop-loss requires --stop-loss-rate")


def require_positive_int(value: int, name: str) -> None:
    if value <= 0:
        raise CliError("invalid_input", f"--{name} must be greater than zero")


def require_positive_number(value: float, name: str) -> None:
    if value <= 0:
        raise CliError("invalid_input", f"--{name} must be greater than zero")


def emit(args: argparse.Namespace, data: Any, *, human: str | None = None) -> None:
    if getattr(args, "json", False):
        print(json.dumps(data, sort_keys=True))
    elif human:
        print(human)
    else:
        print(json.dumps(data, indent=2, sort_keys=True))


def emit_error(args: argparse.Namespace, exc: CliError) -> None:
    error: dict[str, Any] = {
        "ok": False,
        "error": {
            "type": exc.error_type,
            "message": redact(exc.message),
        },
    }
    if exc.status is not None:
        error["error"]["status"] = exc.status
    if getattr(args, "json", False):
        print(json.dumps(error, sort_keys=True))
    else:
        print(f"error: {error['error']['message']}", file=sys.stderr)


def redact(message: str) -> str:
    redacted = message
    for env_name in SECRET_ENV_NAMES:
        value = os.environ.get(env_name)
        if value:
            redacted = redacted.replace(value, "[REDACTED]")
    return redacted


def doctor_human(result: dict[str, Any]) -> str:
    auth = result["auth"]
    network = result.get("network", {})
    lines = [
        f"etoro-api {result['version']}",
        f"base URL: {result['base_url']}",
        f"config: {result['config_path']}",
        f"auth available: {auth['available']} (api={auth['api_key_source']}, user={auth['user_key_source']})",
    ]
    if auth["missing"]:
        lines.append("missing: " + ", ".join(auth["missing"]))
    if result["config_file"]["exists"] and not result["config_file"]["permissions_ok"]:
        lines.append("warning: config file is readable by group/others; run chmod 600 on it")
    if network:
        if network.get("skipped"):
            lines.append("network: skipped")
        elif network.get("reachable"):
            lines.append(f"network: reachable (status {network.get('status')})")
        else:
            lines.append("network: unavailable")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
