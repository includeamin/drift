import json
import re
from collections.abc import Sequence
from typing import Any

from diff.delta import Delta
from diff.json_path import split_pointer


def path_matches(pattern: str, path: str) -> bool:
    """Match a JSON Pointer against a segment-aware glob pattern."""
    pattern_segments = split_pointer(pattern)
    path_segments = split_pointer(path)

    def match(pattern_index: int, path_index: int) -> bool:
        if pattern_index == len(pattern_segments):
            return path_index == len(path_segments)
        segment = pattern_segments[pattern_index]
        if segment == "**":
            return any(
                match(pattern_index + 1, next_path_index)
                for next_path_index in range(path_index, len(path_segments) + 1)
            )
        return (
            path_index < len(path_segments)
            and (segment == "*" or segment == path_segments[path_index])
            and match(pattern_index + 1, path_index + 1)
        )

    return match(0, 0)


def _value_matches(patterns: Sequence[re.Pattern[str]], values: Sequence[Any]) -> bool:
    return any(
        pattern.search(json.dumps(value, ensure_ascii=False)) is not None
        for pattern in patterns
        for value in values
    )


def _compile_patterns(patterns: Sequence[str], flag: str) -> list[re.Pattern[str]]:
    try:
        return [re.compile(pattern) for pattern in patterns]
    except re.error as error:
        raise ValueError(f"invalid {flag} regular expression: {error}") from None


def _resolve(document: Any, path: str) -> Any:
    value = document
    for segment in split_pointer(path):
        if isinstance(value, dict):
            if segment not in value:
                return None
            value = value[segment]
        elif isinstance(value, list):
            try:
                value = value[int(segment)]
            except (IndexError, ValueError):
                return None
        else:
            return None
    return value


def filter_operations(
    operations: Sequence[Delta],
    *,
    old: Any = None,
    paths: Sequence[str] = (),
    fields: Sequence[str] = (),
    values: Sequence[str] = (),
    operations_by_type: Sequence[str] = (),
    invert: bool = False,
) -> list[Delta]:
    """Filter operations; repeated criteria OR together, different criteria AND."""
    field_patterns = _compile_patterns(fields, "--field")
    value_patterns = _compile_patterns(values, "--grep")
    operation_types = set(operations_by_type)

    def matches(operation: Delta) -> bool:
        if paths and not any(
            path_matches(pattern, operation.path) for pattern in paths
        ):
            return False
        if fields:
            field = split_pointer(operation.path)[-1] if operation.path else ""
            if not any(pattern.search(field) for pattern in field_patterns):
                return False
        operation_values: Sequence[Any] = (operation.value,)
        if operation.op in {"remove", "replace"}:
            operation_values = (_resolve(old, operation.path), operation.value)
        if values and not _value_matches(value_patterns, operation_values):
            return False
        return not operation_types or operation.op in operation_types

    return [operation for operation in operations if matches(operation) != invert]
