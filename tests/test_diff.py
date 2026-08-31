import pytest

from diff import Delta, diff, patch
from diff.search import filter_operations, path_matches


def test_path_matches_segment_aware_globs():
    assert path_matches("/users/*/email", "/users/0/email")
    assert not path_matches("/users/*/email", "/users/0/contact/email")
    assert path_matches("/users/**/email", "/users/0/contact/email")
    assert path_matches("/users/**", "/users")
    assert path_matches("/a~1b/*", "/a~1b/c~0d")


def test_filter_operations_combines_criteria():
    operations = [
        Delta(op="add", path="/users/0/email", value="a@example.com"),
        Delta(op="replace", path="/users/1/email", value="b@example.com"),
        Delta(op="replace", path="/users/1/name", value="Bee"),
        Delta(op="remove", path="/settings/debug"),
    ]

    assert filter_operations(operations, paths=["/users/*/email"]) == operations[:2]
    assert filter_operations(operations, fields=["email|debug"]) == [
        operations[0],
        operations[1],
        operations[3],
    ]
    assert filter_operations(
        operations, values=["example\\.com"], operations_by_type=["replace"]
    ) == [operations[1]]
    assert filter_operations(
        operations, old={"settings": {"debug": "enabled"}}, values=["enabled"]
    ) == [operations[3]]
    assert filter_operations(operations, paths=["/users/**"], invert=True) == [
        operations[3]
    ]


@pytest.mark.parametrize(
    ("argument", "flag"), [("fields", "--field"), ("values", "--grep")]
)
def test_filter_operations_reports_invalid_regular_expressions(argument, flag):
    with pytest.raises(ValueError, match=rf"invalid {flag} regular expression"):
        filter_operations([], **{argument: ["*"]})


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
        # deeply nested scalar change
        ({"a": {"b": {"c": {"d": 1}}}}, {"a": {"b": {"c": {"d": 2}}}}),
        # dicts nested inside lists inside dicts
        (
            {"users": [{"id": 1, "tags": ["x"]}, {"id": 2, "tags": []}]},
            {"users": [{"id": 1, "tags": ["x", "y"]}, {"id": 2, "tags": []}]},
        ),
        # lists of lists
        ({"m": [[1, 2], [3, 4]]}, {"m": [[1, 9], [3, 4], [5]]}),
        # container type flips at depth
        ({"a": {"b": {"c": 1}}}, {"a": {"b": [1, 2]}}),
        ({"a": {"b": [1, 2]}}, {"a": {"b": None}}),
        # nested structure grows and shrinks
        ({"a": {"b": {"c": {"d": {"e": 1}}}}}, {"a": {}}),
        ({"a": {}}, {"a": {"b": {"c": {"d": {"e": 1}}}}}),
        # escaped tokens at multiple levels
        ({"a~b": {"c/d": {"~/": 1}}}, {"a~b": {"c/d": {"~/": 2}}}),
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


def test_deep_change_emits_one_targeted_operation():
    old = {"a": {"b": {"c": {"d": 1, "e": 2}}}}
    new = {"a": {"b": {"c": {"d": 99, "e": 2}}}}
    assert diff(new, old) == [Delta(op="replace", path="/a/b/c/d", value=99)]


def test_change_inside_list_of_dicts_does_not_rewrite_the_list():
    old = {"users": [{"id": 1, "n": "a"}, {"id": 2, "n": "b"}]}
    new = {"users": [{"id": 1, "n": "a"}, {"id": 2, "n": "B"}]}
    assert diff(new, old) == [Delta(op="replace", path="/users/1/n", value="B")]


def test_unchanged_deep_siblings_are_not_emitted():
    old = {"keep": {"x": [1, 2, 3]}, "touch": {"y": 1}}
    new = {"keep": {"x": [1, 2, 3]}, "touch": {"y": 2}}
    assert diff(new, old) == [Delta(op="replace", path="/touch/y", value=2)]


def test_nested_escaping_is_applied_per_segment():
    old = {"a~b": {"c/d": 1}}
    new = {"a~b": {"c/d": 2}}
    assert diff(new, old) == [Delta(op="replace", path="/a~0b/c~1d", value=2)]


@pytest.mark.xfail(reason="positional array diff, no LCS/Myers alignment", strict=True)
def test_list_front_insert_should_be_a_single_add():
    old = {"l": [1, 2, 3, 4, 5, 6]}
    new = {"l": [0, 1, 2, 3, 4, 5, 6]}
    assert diff(new, old) == [Delta(op="add", path="/l/0", value=0)]


@pytest.mark.xfail(
    reason="no cost cutoff to collapse a fully rewritten subtree", strict=True
)
def test_fully_replaced_subtree_should_collapse_to_one_replace():
    old = {"a": {"x": 1, "y": 2, "z": 3}}
    new = {"a": {"p": 1, "q": 2, "r": 3}}
    assert diff(new, old) == [Delta(op="replace", path="/a", value=new["a"])]


@pytest.mark.xfail(
    reason="no move detection, value is duplicated in the patch", strict=True
)
def test_renamed_key_should_be_a_move():
    payload = {"big": [1, 2, 3, 4, 5]}
    assert diff({"new": payload}, {"old": payload}) == [
        Delta(op="move", path="/new", from_path="/old")
    ]
