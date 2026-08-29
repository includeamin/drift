from collections.abc import Iterator
from typing import Any


def escape_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def unescape_token(token: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(token):
        if token[index] != "~":
            result.append(token[index])
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in "01":
            raise ValueError(f"Invalid JSON Pointer escape in {token!r}")
        result.append("~" if token[index + 1] == "0" else "/")
        index += 2
    return "".join(result)


def join_pointer(path: str, token: str | int) -> str:
    return f"{path}/{escape_token(str(token))}"


def split_pointer(path: str) -> list[str]:
    if path == "":
        return []
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("JSON Pointer must be empty or start with '/'")
    return [unescape_token(token) for token in path[1:].split("/")]


def iter_json_paths(
    obj: Any,
    *,
    include_root: bool = False,
    leaves_only: bool = True,
    include_containers: bool = False,
    include_values: bool = False,
    sort_keys: bool = False,
    max_depth: int | None = None,
) -> Iterator[str | tuple[str, Any]]:
    def emit(path: str, value: Any) -> str | tuple[str, Any]:
        return (path, value) if include_values else path

    def walk(value: Any, path: str, depth: int) -> Iterator[str | tuple[str, Any]]:
        if max_depth is not None and depth > max_depth:
            return
        container = isinstance(value, (dict, list))
        if include_containers and (not leaves_only or not value):
            yield emit(path, value)
        if isinstance(value, dict):
            keys = sorted(value) if sort_keys else value
            for key in keys:
                yield from walk(value[key], join_pointer(path, key), depth + 1)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                yield from walk(item, join_pointer(path, index), depth + 1)
        elif not container and (path or include_root):
            yield emit(path, value)

    yield from walk(obj, "", 0)


def list_json_paths(obj: Any, **kwargs: Any) -> list[str | tuple[str, Any]]:
    return list(iter_json_paths(obj, **kwargs))


def paths_with_values(obj: Any, **kwargs: Any) -> list[tuple[str, Any]]:
    kwargs["include_values"] = True
    return [item for item in iter_json_paths(obj, **kwargs) if isinstance(item, tuple)]


def path_value_map(obj: Any, **kwargs: Any) -> dict[str, Any]:
    return dict(paths_with_values(obj, **kwargs))
