# diff

Calculate RFC 6902 JSON Patch operations between JSON-compatible Python values.
Paths use RFC 6901 JSON Pointer syntax.

## Usage

```python
from diff import diff, patch

old = {"name": "David"}
new = {"name": "Alex"}
operations = diff(new, old)

assert operations[0].op == "replace"
assert operations[0].path == "/name"
assert operations[0].value == "Alex"
assert patch(old, operations) == new
```

The returned `Delta` objects correspond to JSON Patch operation objects and use
the standard `op`, `path`, `value`, and `from_path` fields. `patch` also accepts
ordinary operation dictionaries using RFC names, including `from`.

Arrays use RFC semantics: `add` inserts, `remove` shifts later elements, and
`replace` updates an existing element. The empty path `""` addresses the
document root.

## Supported Formats

- [x] JSON
- [ ] YAML
- [ ] XML
- [ ] TOML

## Install

```bash
poetry add git+https://github.com/includeamin/diff.git#tag
```
