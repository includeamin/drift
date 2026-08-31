"""Best-effort XML<->JSON mapping (experimental, not guaranteed round-trip safe).

Convention: element attributes become ``@name`` keys, text content becomes a
``#text`` key (or a bare scalar for leaf elements with no attributes/children),
and repeated sibling tags become a list. Comments, processing instructions,
namespaces and mixed content are not preserved.
"""

import xml.etree.ElementTree as ET
from typing import Any

from diff.json_path import split_pointer


def _elem_to_obj(elem: ET.Element) -> Any:
    obj: dict[str, Any] = {f"@{key}": value for key, value in elem.attrib.items()}

    children_by_tag: dict[str, list[Any]] = {}
    for child in elem:
        children_by_tag.setdefault(child.tag, []).append(_elem_to_obj(child))
    for tag, items in children_by_tag.items():
        obj[tag] = items if len(items) > 1 else items[0]

    text = (elem.text or "").strip()
    if text:
        if obj:
            obj["#text"] = text
        else:
            return text
    return obj


def _obj_to_elem(tag: str, obj: Any) -> ET.Element:
    elem = ET.Element(tag)
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.startswith("@"):
                elem.set(key[1:], str(value))
            elif key == "#text":
                elem.text = str(value)
            elif isinstance(value, list):
                for item in value:
                    elem.append(_obj_to_elem(key, item))
            else:
                elem.append(_obj_to_elem(key, value))
    elif obj is not None:
        elem.text = str(obj)
    return elem


class XmlFormat:
    name = "xml"
    extensions = (".xml",)

    def load(self, text: str) -> Any:
        # CLI-supplied local files only, same trust level as JSON/YAML/TOML inputs.
        root = ET.fromstring(text)  # noqa: S314
        return {root.tag: _elem_to_obj(root)}

    def dump(self, value: Any) -> str:
        if not isinstance(value, dict) or len(value) != 1:
            raise ValueError("XML documents must have exactly one root element")
        ((tag, obj),) = value.items()
        elem = _obj_to_elem(tag, obj)
        ET.indent(elem)
        return ET.tostring(elem, encoding="unicode") + "\n"

    def render_path(self, path: str) -> str:
        segments = split_pointer(path)
        if not segments:
            return "/"
        parts: list[str] = []
        for segment in segments:
            if segment.isdigit():
                if parts:
                    parts[-1] = f"{parts[-1]}[{int(segment) + 1}]"
                continue
            parts.append(segment)
        return "/" + "/".join(parts)
