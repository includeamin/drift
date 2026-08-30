from typing import Any

import yaml


class YamlFormat:
    name = "yaml"
    extensions = (".yaml", ".yml")

    def load(self, text: str) -> Any:
        return yaml.safe_load(text)

    def dump(self, value: Any) -> str:
        return yaml.safe_dump(value, sort_keys=False, allow_unicode=True)

    def render_path(self, path: str) -> str:
        return path
