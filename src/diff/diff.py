from diff import json_path
from diff.delta import Delta, JsonValue


def _path_sort_key(path: str) -> tuple[tuple[int, str | int], ...]:
    return tuple(
        (0, token) if isinstance(token, str) else (1, token)
        for token in json_path.tokenize_json_path(path)
    )


def diff(new: JsonValue, old: JsonValue) -> list[Delta]:
    if new == old:
        return []

    if (
        not isinstance(new, (dict, list))
        or not isinstance(old, (dict, list))
        or type(new) is not type(old)
    ):
        return [Delta(path="$", operation="modified", old_value=old, new_value=new)]

    new_path_map = json_path.path_value_map(
        new, include_root=True, leaves_only=True, include_containers=True
    )
    old_path_map = json_path.path_value_map(
        old, include_root=True, leaves_only=True, include_containers=True
    )
    new_path_map.pop("$", None)
    old_path_map.pop("$", None)
    operations: list[Delta] = []

    deleted = old_path_map.keys() - new_path_map.keys()
    for key in sorted(deleted, key=_path_sort_key, reverse=True):
        operations.append(  # noqa: PERF401
            Delta(
                path=key,
                operation="deleted",
                old_value=old_path_map[key],
                new_value=None,
            )
        )

    added = new_path_map.keys() - old_path_map.keys()
    for key in sorted(added, key=_path_sort_key):
        operations.append(  # noqa: PERF401
            Delta(
                path=key, operation="added", old_value=None, new_value=new_path_map[key]
            )
        )

    shared_keys = new_path_map.keys() & old_path_map.keys()
    for key in sorted(shared_keys, key=_path_sort_key):
        if old_path_map[key] != new_path_map[key]:
            operations.append(  # noqa: PERF401
                Delta(
                    path=key,
                    operation="modified",
                    old_value=old_path_map[key],
                    new_value=new_path_map[key],
                )
            )
    return operations
