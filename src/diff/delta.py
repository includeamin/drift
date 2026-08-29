import dataclasses
import typing


@dataclasses.dataclass
class Delta:
    op: typing.Literal["add", "remove", "replace", "move", "copy", "test"]
    path: str
    value: typing.Any = None
    from_path: str | None = None

    def __repr__(self):
        fields = [f'"op": {self.op!r}', f'"path": {self.path!r}']
        if self.op in {"add", "replace", "test"}:
            fields.append(f'"value": {self.value!r}')
        if self.op in {"move", "copy"}:
            fields.append(f'"from": {self.from_path!r}')
        return "{" + ", ".join(fields) + "}"
