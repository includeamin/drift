import copy
from collections.abc import Mapping
from typing import Any

from diff.delta import Delta
from diff.json_path import split_pointer


def _operation(op: Delta | Mapping[str, Any]) -> tuple[str, str, Any, str | None]:
    if isinstance(op, Delta):
        return op.op, op.path, op.value, op.from_path
    return op["op"], op["path"], op.get("value"), op.get("from")


def _index(segment: str, length: int, *, allow_end: bool = False) -> int:
    if not segment.isdigit() or (segment != "0" and segment.startswith("0")):
        raise ValueError(f"Invalid array index {segment!r}")
    index = int(segment)
    if index > length or (index == length and not allow_end):
        raise IndexError(f"Array index {index} out of range")
    return index


def _parent(document: Any, path: str) -> tuple[Any, str]:
    segments = split_pointer(path)
    if not segments:
        raise ValueError("The root has no parent")
    current = document
    for segment in segments[:-1]:
        if isinstance(current, dict):
            if segment not in current:
                raise KeyError(segment)
            current = current[segment]
        elif isinstance(current, list):
            current = current[_index(segment, len(current))]
        else:
            raise TypeError("Cannot traverse a scalar value")
    return current, segments[-1]


def _get(document: Any, path: str) -> Any:
    current = document
    for segment in split_pointer(path):
        if isinstance(current, dict):
            current = current[segment]
        elif isinstance(current, list):
            current = current[_index(segment, len(current))]
        else:
            raise TypeError("Cannot traverse a scalar value")
    return current


def _add(document: Any, path: str, value: Any) -> Any:
    if path == "":
        return copy.deepcopy(value)
    parent, segment = _parent(document, path)
    if isinstance(parent, dict):
        parent[segment] = copy.deepcopy(value)
    elif isinstance(parent, list):
        index = (
            len(parent)
            if segment == "-"
            else _index(segment, len(parent), allow_end=True)
        )
        parent.insert(index, copy.deepcopy(value))
    else:
        raise TypeError("Cannot add to a scalar value")
    return document


def _remove(document: Any, path: str) -> Any:
    if path == "":
        raise ValueError("Removing the document root is not supported")
    parent, segment = _parent(document, path)
    if isinstance(parent, dict):
        del parent[segment]
    elif isinstance(parent, list):
        del parent[_index(segment, len(parent))]
    else:
        raise TypeError("Cannot remove from a scalar value")
    return document


def _replace(document: Any, path: str, value: Any) -> Any:
    if path == "":
        return copy.deepcopy(value)
    parent, segment = _parent(document, path)
    if isinstance(parent, dict):
        if segment not in parent:
            raise KeyError(segment)
        parent[segment] = copy.deepcopy(value)
    elif isinstance(parent, list):
        parent[_index(segment, len(parent))] = copy.deepcopy(value)
    else:
        raise TypeError("Cannot replace in a scalar value")
    return document


def patch(base: Any, deltas: list[Delta | Mapping[str, Any]]) -> Any:
    output = copy.deepcopy(base)
    for operation in deltas:
        op, path, value, from_path = _operation(operation)
        if op == "add":
            output = _add(output, path, value)
        elif op == "remove":
            output = _remove(output, path)
        elif op == "replace":
            output = _replace(output, path, value)
        elif op == "test":
            if _get(output, path) != value:
                raise ValueError(f"JSON Patch test failed at {path!r}")
        elif op in {"move", "copy"}:
            if from_path is None:
                raise ValueError(f"{op!r} requires a 'from' path")
            source = copy.deepcopy(_get(output, from_path))
            if op == "move":
                _remove(output, from_path)
            output = _add(output, path, source)
        else:
            raise ValueError(f"Unsupported JSON Patch operation {op!r}")
    return output
