import json
import os
from typing import Any, Dict, List, Optional


DEFAULT_CONFIG_FILE = "config.json"


def load_runtime_config(args) -> Dict[str, Any]:
    config_path = getattr(args, "config_path", None) or _detect_default_config_path()
    config_values = load_config_file(config_path) if config_path else {}

    raw_categories = _pick_value(args.categories, config_values.get("categories"))
    settings: Dict[str, Any] = {
        "config_path": config_path,
        "token": _pick_value(args.token, config_values.get("token")),
        "chat_id": _parse_optional_int(_pick_value(args.chat_id, config_values.get("chat_id"))),
        "categories": _parse_categories(raw_categories),
        "interval": _parse_optional_int(
            _pick_value(args.interval, config_values.get("interval"))
        ) or 300,
        "bootstrap_mode": _pick_value(
            args.bootstrap_mode,
            config_values.get("bootstrap_mode"),
        ) or "send",
        "state_file": _pick_value(
            args.state_file,
            config_values.get("state_file"),
        ) or "sent_orders.json",
        "max_state_orders": _parse_optional_int(
            _pick_value(
                args.max_state_orders,
                config_values.get("max_state_orders"),
            )
        ) or 5000,
        "dry_run": bool(args.dry_run or config_values.get("dry_run")),
        "once": bool(args.once or config_values.get("once")),
        "log_level": _pick_value(
            args.log_level,
            config_values.get("log_level"),
        ) or "INFO",
    }
    return settings


def _detect_default_config_path() -> Optional[str]:
    if os.path.exists(DEFAULT_CONFIG_FILE):
        return DEFAULT_CONFIG_FILE
    return None


def load_config_file(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except FileNotFoundError as exc:
        raise SystemExit(f"Configuration file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in configuration file {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise SystemExit(f"Configuration file must contain a JSON object: {path}")
    return payload


def _pick_value(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _parse_optional_int(value: Optional[Any]) -> Optional[int]:
    if value in (None, ""):
        return None
    return int(value)


def _parse_optional_bool(value: Optional[Any]) -> Optional[bool]:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _parse_categories(value: Optional[Any]) -> List[int]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [int(item) for item in value]

    normalized = str(value).replace(",", " ")
    return [int(part) for part in normalized.split() if part]
