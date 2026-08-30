"""Pluggable structured-data formats: each adapter converts to/from the
JSON-compatible values that diff/patch/render already operate on."""

from typing import Any, Protocol


class Format(Protocol):
    name: str
    extensions: tuple[str, ...]

    def load(self, text: str) -> Any: ...

    def dump(self, value: Any) -> str: ...

    def render_path(self, path: str) -> str:
        """Convert a JSON Pointer into this format's native path notation."""
        ...


_FORMATS: dict[str, Format] = {}
_EXTENSIONS: dict[str, Format] = {}


def register(fmt: Format) -> None:
    _FORMATS[fmt.name] = fmt
    for extension in fmt.extensions:
        _EXTENSIONS[extension] = fmt


def by_name(name: str) -> Format:
    try:
        return _FORMATS[name]
    except KeyError:
        available = ", ".join(sorted(_FORMATS))
        raise ValueError(f"Unknown format {name!r}; available: {available}") from None


def by_extension(path: str) -> Format:
    _, _, extension = path.rpartition(".")
    if not extension:
        return _FORMATS["json"]
    return _EXTENSIONS.get(f".{extension}", _FORMATS["json"])


def resolve(explicit: str | None, path: str) -> Format:
    if explicit is not None:
        return by_name(explicit)
    return by_extension(path)


def available_names() -> list[str]:
    return sorted(_FORMATS)


from diff.formats.json_format import JsonFormat  # noqa: E402
from diff.formats.toml_format import TomlFormat  # noqa: E402
from diff.formats.xml_format import XmlFormat  # noqa: E402
from diff.formats.yaml_format import YamlFormat  # noqa: E402

register(JsonFormat())
register(YamlFormat())
register(TomlFormat())
register(XmlFormat())
