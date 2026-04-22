"""Logging configuration with a defensive redaction filter.

The filter scrubs API-key-like strings from every log record before formatting.
It is intentionally aggressive: if in doubt, we redact.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterable

REDACTED = "***REDACTED***"

_KEY_ENV_SUFFIX = "_API_KEY"

_KEY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{10,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{10,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{10,}", re.IGNORECASE),
)


def _collect_env_secret_values() -> list[str]:
    values: list[str] = []
    for name, value in os.environ.items():
        if not value:
            continue
        if name.endswith(_KEY_ENV_SUFFIX) and len(value.strip()) >= 8:
            values.append(value.strip())
    return values


def redact(text: str, extra_literals: Iterable[str] = ()) -> str:
    """Return `text` with all detected secrets replaced by `REDACTED`.

    `extra_literals` lets callers (and the `RedactionFilter`) strip exact values
    fetched from the environment, covering keys that don't match any regex.
    """
    if not text:
        return text

    out = text
    for literal in extra_literals:
        if literal and len(literal) >= 8:
            out = out.replace(literal, REDACTED)
    for pattern in _KEY_PATTERNS:
        out = pattern.sub(REDACTED, out)
    return out


class RedactionFilter(logging.Filter):
    """Scrubs API-key-like strings from log messages and arguments."""

    def filter(self, record: logging.LogRecord) -> bool:
        extras = tuple(_collect_env_secret_values())

        if isinstance(record.msg, str):
            record.msg = redact(record.msg, extras)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: _redact_value(v, extras) for k, v in record.args.items()}
            else:
                record.args = tuple(_redact_value(a, extras) for a in record.args)

        return True


def _redact_value(value: object, extras: tuple[str, ...]) -> object:
    if isinstance(value, str):
        return redact(value, extras)
    return value


def configure_logging(level: int = logging.INFO) -> None:
    """Install a root handler with the redaction filter. Idempotent."""
    root = logging.getLogger()
    root.setLevel(level)

    for handler in list(root.handlers):
        if getattr(handler, "_game2048_installed", False):
            return

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(RedactionFilter())
    handler._game2048_installed = True  # type: ignore[attr-defined]

    root.addHandler(handler)
