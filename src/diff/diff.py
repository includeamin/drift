from typing import Any

from diff.delta import Delta
from diff.json_path import join_pointer


def _equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _equal(old_value, new_value)
            for old_value, new_value in zip(left, right, strict=True)
        )
    return left == right


def _diff(new: Any, old: Any, path: str, operations: list[Delta]) -> None:
    if isinstance(old, dict) and isinstance(new, dict):
        operations.extend(
            Delta(op="remove", path=join_pointer(path, key))
            for key in sorted(old.keys() - new.keys())
        )
        operations.extend(
            Delta(op="add", path=join_pointer(path, key), value=new[key])
            for key in sorted(new.keys() - old.keys())
        )
        for key in sorted(old.keys() & new.keys()):
            _diff(new[key], old[key], join_pointer(path, key), operations)
        return

    if isinstance(old, list) and isinstance(new, list):
        for index in range(min(len(old), len(new))):
            _diff(new[index], old[index], join_pointer(path, index), operations)
        operations.extend(
            Delta(op="remove", path=join_pointer(path, index))
            for index in range(len(old) - 1, len(new) - 1, -1)
        )
        operations.extend(
            Delta(op="add", path=join_pointer(path, index), value=new[index])
            for index in range(len(old), len(new))
        )
        return

    if not _equal(old, new):
        operations.append(Delta(op="replace", path=path, value=new))


def diff(new: Any, old: Any) -> list[Delta]:
    operations: list[Delta] = []
    _diff(new, old, "", operations)
    return operations
