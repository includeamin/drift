import tomllib
from typing import Any

import tomli_w

from diff.json_path import split_pointer


class TomlFormat:
    name = "toml"
    extensions = (".toml",)

    def load(self, text: str) -> Any:
        return tomllib.loads(text)

    def dump(self, value: Any) -> str:
        return tomli_w.dumps(value)

    def render_path(self, path: str) -> str:
        segments = split_pointer(path)
        return ".".join(segments) if segments else "."
