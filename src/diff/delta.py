import dataclasses
import typing

JsonScalar: typing.TypeAlias = str | int | float | bool | None
JsonValue: typing.TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclasses.dataclass
class Delta:
    operation: typing.Literal["deleted", "modified", "added"]
    path: str
    new_value: JsonValue
    old_value: JsonValue

    def __repr__(self):
        return (
            f"Delta(operation='{self.operation}', path='{self.path}', "
            f"new_value={self.new_value!r}, old_value={self.old_value!r})"
        )
