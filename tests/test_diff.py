import pytest

from diff import Delta, diff, patch


def test_replace_operation():
    assert diff({"name": "Alex"}, {"name": "David"}) == [
        Delta(op="replace", path="/name", value="Alex")
    ]


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ({}, {"settings": {}, "items": []}),
        ({"a": 1}, {"a": 2, "b": {"c": "x"}}),
        ({"list": [1, 2, 3]}, {"list": [1, 4, 3, 5]}),
        ({"a/b~c": 1}, {"a/b~c": 2}),
        ({"n": None}, {"n": 0}),
        ({"a": 1}, []),
    ],
)
def test_diff_patch_roundtrip(old, new):
    operations = diff(new, old)
    assert patch(old, operations) == new
    assert patch(new, diff(old, new)) == old


def test_array_add_inserts_and_remove_shifts():
    assert patch([1, 2], [{"op": "add", "path": "/1", "value": 9}]) == [1, 9, 2]
    assert patch([1, 2, 3], [{"op": "remove", "path": "/1"}]) == [1, 3]
    assert patch([1], [{"op": "add", "path": "/-", "value": 2}]) == [1, 2]


def test_all_standard_operations():
    assert patch({"a": 1}, [{"op": "copy", "from": "/a", "path": "/b"}]) == {
        "a": 1,
        "b": 1,
    }
    assert patch({"a": 1}, [{"op": "move", "from": "/a", "path": "/b"}]) == {"b": 1}
    assert patch({"a": 1}, [{"op": "test", "path": "/a", "value": 1}]) == {"a": 1}


def test_invalid_test_fails():
    with pytest.raises(ValueError, match="test failed"):
        patch({"a": 1}, [{"op": "test", "path": "/a", "value": 2}])
