# diff

Calculate RFC 6902 JSON Patch operations between JSON-compatible Python values.
Paths use RFC 6901 JSON Pointer syntax.

Ships as both a Python library and a `drift` command-line tool.

## Install the CLI

`drift` is distributed as a [zipapp](https://docs.python.org/3/library/zipapp.html):
one self-contained executable with its dependencies (PyYAML, tomli-w) bundled
in, so nothing needs to be installed separately. Installing needs nothing but
Python 3.11+, `git` and `pip`.

```bash
curl -fsSL https://raw.githubusercontent.com/includeamin/drift/main/install.sh | bash
```

Or from a clone:

```bash
bash install.sh
```

This clones the latest tagged release, builds the executable and installs it to
`~/.local/bin/drift`.

### Staying up to date

```bash
bash install.sh --check     # report whether a newer release exists
bash install.sh --update    # install only if a newer release exists
```

`--check` exits `0` when you are current and `10` when an update is available,
which makes it easy to use in a shell prompt or a cron job.

### Installer options

| Command | Effect |
| --- | --- |
| `bash install.sh` | Install or reinstall the latest release |
| `bash install.sh --check` | Report whether a newer release exists |
| `bash install.sh --update` | Install only if a newer release exists |
| `bash install.sh --ref v0.5.0` | Install a specific tag, branch or commit |
| `bash install.sh --local` | Build from the working tree instead of GitHub |
| `bash install.sh --uninstall` | Remove `drift` and its cached checkout |

`PREFIX` (default `~/.local`), `BIN_DIR` and `REPO_URL` are honoured as
environment variables. A build that fails verification never replaces a working
installation.

## CLI usage

Every command reads `-` as stdin and accepts `-o/--output`, `--indent` and
`--compact`. `diff`, `patch`, `paths` and `check` also accept `--format
{json,yaml,toml,xml}`, which defaults to detecting the format from the file
extension (falling back to JSON).

### `drift diff OLD NEW`

Emit the JSON Patch that turns `OLD` into `NEW`.

```bash
$ drift diff old.json new.json --compact
[{"op": "replace", "path": "/meta/v", "value": 2}, {"op": "add", "path": "/tags/2", "value": "c"}]
```

Add `--stats` for a summary instead of the operations, and `--exit-code` to exit
`1` when the documents differ:

```bash
$ drift diff old.json new.json --stats --compact
{"total": 3, "by_op": {"add": 1, "replace": 2}}
```

Add `--pretty` for a colored, human-readable rendering instead of JSON Patch:

```bash
$ drift diff old.json new.json --pretty
+ /tags/2: "c"
~ /meta/v: 1 → 2
```

Colors are used automatically on a TTY and disabled when piping; pass
`--no-color`, or set the `NO_COLOR`/`FORCE_COLOR` environment variables, to
override the detection.

### `drift patch DOCUMENT PATCH`

Apply a JSON Patch array to a document. `--in-place` rewrites the file.

```bash
drift diff old.json new.json -o patch.json
drift patch old.json patch.json
```

### `drift paths DOCUMENT`

List the JSON Pointers in a document, one per line.

```bash
$ drift paths new.json
/name
/tags/0
/meta/v
```

`--values` emits a pointer-to-value object instead; `--containers`,
`--include-root`, `--sort-keys` and `--max-depth N` control the traversal.

### `drift check OLD NEW`

Verify that the generated patch round-trips, exiting non-zero if it does not.

```bash
$ drift check old.json new.json --compact
{"roundtrip": true, "operations": 3}
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Documents differ (`--exit-code`), round-trip failed, or a patch operation failed |
| `2` | Invalid JSON or an I/O error |

## Library usage

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
- [x] YAML
- [x] XML (experimental, lossy — see [src/diff/formats/xml_format.py](src/diff/formats/xml_format.py))
- [x] TOML

## Install as a library

```bash
poetry add git+https://github.com/includeamin/drift.git#tag
```

## Versioning

The release workflow is the single source of truth for the version. It derives
the next version from the latest git tag and writes the same value to the git
tag, `pyproject.toml` and `diff.__version__`, so `drift --version` always
matches the release you installed. CI fails if those values ever drift apart.
