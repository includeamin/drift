"""Human-readable rendering of a list of JSON Patch operations."""

import json
import os
import sys
from typing import TYPE_CHECKING, Any

from diff.delta import Delta
from diff.json_path import split_pointer

if TYPE_CHECKING:
    from diff.formats import Format

_RESET = "\033[0m"
_COLORS = {
    "add": "\033[32m",
    "remove": "\033[31m",
    "replace": "\033[33m",
    "move": "\033[36m",
    "copy": "\033[36m",
    "test": "\033[36m",
}
_SYMBOLS = {
    "add": "+",
    "remove": "-",
    "replace": "~",
    "move": "m",
    "copy": "c",
    "test": "?",
}


def supports_color(stream: Any = sys.stdout) -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("FORCE_COLOR") is not None:
        return True
    return hasattr(stream, "isatty") and stream.isatty()


def _resolve(document: Any, path: str) -> Any:
    value = document
    for segment in split_pointer(path):
        if isinstance(value, list):
            value = value[int(segment)]
        elif isinstance(value, dict):
            value = value[segment]
        else:
            return None
    return value


def _format_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_pretty(
    operations: list[Delta],
    old: Any,
    *,
    color: bool = True,
    format: "Format | None" = None,
) -> str:
    render_path = format.render_path if format is not None else (lambda path: path)
    lines: list[str] = []
    for operation in operations:
        symbol = _SYMBOLS[operation.op]
        prefix = f"{_COLORS[operation.op]}{symbol}{_RESET}" if color else symbol
        path = render_path(operation.path)

        if operation.op == "add":
            lines.append(f"{prefix} {path}: {_format_value(operation.value)}")
        elif operation.op == "remove":
            old_value = _resolve(old, operation.path)
            lines.append(f"{prefix} {path}: {_format_value(old_value)}")
        elif operation.op == "replace":
            old_value = _resolve(old, operation.path)
            new_value = _format_value(operation.value)
            lines.append(
                f"{prefix} {path}: {_format_value(old_value)} \u2192 {new_value}"
            )
        elif operation.op in {"move", "copy"}:
            lines.append(
                f"{prefix} {path} \u2190 {render_path(operation.from_path or '')}"
            )
        else:  # test
            lines.append(f"{prefix} {path}: {_format_value(operation.value)}")
    return "\n".join(lines)
