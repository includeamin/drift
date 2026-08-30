import json
from typing import Any


class JsonFormat:
    name = "json"
    extensions = (".json",)

    def load(self, text: str) -> Any:
        return json.loads(text)

    def dump(self, value: Any) -> str:
        return json.dumps(value, indent=2, ensure_ascii=False) + "\n"

    def render_path(self, path: str) -> str:
        return path
