import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any

from diff import __version__
from diff.delta import Delta
from diff.diff import diff
from diff.json_path import list_json_paths, paths_with_values
from diff.patch import patch
from diff.render import render_pretty, supports_color

PROGRAM = "jdiff"


def _delta_to_dict(delta: Delta) -> dict[str, Any]:
    payload: dict[str, Any] = {"op": delta.op, "path": delta.path}
    if delta.op in {"add", "replace", "test"}:
        payload["value"] = delta.value
    if delta.op in {"move", "copy"}:
        payload["from"] = delta.from_path
    return payload


def _read_json(source: str) -> Any:
    if source == "-":
        return json.load(sys.stdin)
    with open(source, encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(value: Any, destination: str | None, indent: int | None) -> None:
    text = json.dumps(value, indent=indent, ensure_ascii=False, sort_keys=False)
    if destination is None or destination == "-":
        sys.stdout.write(text + "\n")
        return
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")


def _write_text(text: str, destination: str | None) -> None:
    if destination is None or destination == "-":
        sys.stdout.write(text + "\n")
        return
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")


def _indent(args: argparse.Namespace) -> int | None:
    return None if args.compact else args.indent


def _cmd_diff(args: argparse.Namespace) -> int:
    old = _read_json(args.old)
    new = _read_json(args.new)
    operations = diff(new, old)

    if args.pretty:
        color = supports_color() if not args.no_color else False
        _write_text(render_pretty(operations, old, color=color), args.output)
    elif args.stats:
        counts: dict[str, int] = {}
        for operation in operations:
            counts[operation.op] = counts.get(operation.op, 0) + 1
        summary = {"total": len(operations), "by_op": dict(sorted(counts.items()))}
        _write_json(summary, args.output, _indent(args))
    else:
        payload = [_delta_to_dict(operation) for operation in operations]
        _write_json(payload, args.output, _indent(args))

    if args.exit_code and operations:
        return 1
    return 0


def _cmd_patch(args: argparse.Namespace) -> int:
    document = _read_json(args.document)
    operations = _read_json(args.patch)
    if not isinstance(operations, list):
        raise ValueError("A JSON Patch document must be an array of operations")

    result = patch(document, operations)
    destination = args.document if args.in_place else args.output
    if args.in_place and args.document == "-":
        raise ValueError("--in-place cannot be used when reading from stdin")
    _write_json(result, destination, _indent(args))
    return 0


def _cmd_paths(args: argparse.Namespace) -> int:
    document = _read_json(args.document)
    options: dict[str, Any] = {
        "include_root": args.include_root,
        "include_containers": args.containers,
        "sort_keys": args.sort_keys,
        "max_depth": args.max_depth,
    }

    if args.values:
        pairs = paths_with_values(document, **options)
        _write_json(dict(pairs), args.output, _indent(args))
        return 0

    paths = list_json_paths(document, **options)
    if args.output in (None, "-") and not args.json:
        for path in paths:
            sys.stdout.write(f"{path}\n")
        return 0
    _write_json(paths, args.output, _indent(args))
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    old = _read_json(args.old)
    new = _read_json(args.new)
    operations = diff(new, old)
    rebuilt = patch(old, operations)
    ok = rebuilt == new
    _write_json(
        {"roundtrip": ok, "operations": len(operations)}, args.output, _indent(args)
    )
    return 0 if ok else 1


def _add_output_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-o", "--output", default=None, help="Write to a file instead of stdout"
    )
    parser.add_argument(
        "--indent", type=int, default=2, help="Indentation width (default: 2)"
    )
    parser.add_argument(
        "--compact", action="store_true", help="Emit single-line JSON output"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="RFC 6902 JSON Patch tooling: diff, patch and inspect JSON documents.",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"{PROGRAM} {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    diff_parser = subparsers.add_parser(
        "diff", help="Emit the JSON Patch that turns OLD into NEW"
    )
    diff_parser.add_argument("old", help="Path to the original document, or '-'")
    diff_parser.add_argument("new", help="Path to the updated document, or '-'")
    diff_parser.add_argument(
        "--stats", action="store_true", help="Print an operation-count summary instead"
    )
    diff_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Render a human-readable colored diff instead of JSON Patch",
    )
    diff_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in --pretty output (also honors NO_COLOR env var)",
    )
    diff_parser.add_argument(
        "--exit-code", action="store_true", help="Exit 1 when the documents differ"
    )
    _add_output_flags(diff_parser)
    diff_parser.set_defaults(handler=_cmd_diff)

    patch_parser = subparsers.add_parser(
        "patch", help="Apply a JSON Patch document to a JSON document"
    )
    patch_parser.add_argument("document", help="Path to the document, or '-'")
    patch_parser.add_argument("patch", help="Path to the JSON Patch array, or '-'")
    patch_parser.add_argument(
        "--in-place", action="store_true", help="Rewrite the document file in place"
    )
    _add_output_flags(patch_parser)
    patch_parser.set_defaults(handler=_cmd_patch)

    paths_parser = subparsers.add_parser(
        "paths", help="List the JSON Pointers contained in a document"
    )
    paths_parser.add_argument("document", help="Path to the document, or '-'")
    paths_parser.add_argument(
        "--values", action="store_true", help="Emit a pointer-to-value object"
    )
    paths_parser.add_argument(
        "--containers", action="store_true", help="Include object and array pointers"
    )
    paths_parser.add_argument(
        "--include-root", action="store_true", help="Include the empty root pointer"
    )
    paths_parser.add_argument(
        "--sort-keys", action="store_true", help="Visit object keys in sorted order"
    )
    paths_parser.add_argument(
        "--max-depth", type=int, default=None, help="Stop descending past this depth"
    )
    paths_parser.add_argument(
        "--json", action="store_true", help="Emit a JSON array instead of plain lines"
    )
    _add_output_flags(paths_parser)
    paths_parser.set_defaults(handler=_cmd_paths)

    check_parser = subparsers.add_parser(
        "check", help="Verify that diff(OLD, NEW) round-trips through patch"
    )
    check_parser.add_argument("old", help="Path to the original document, or '-'")
    check_parser.add_argument("new", help="Path to the updated document, or '-'")
    _add_output_flags(check_parser)
    check_parser.set_defaults(handler=_cmd_apply)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except BrokenPipeError:
        return 0
    except json.JSONDecodeError as error:
        parser.exit(2, f"{PROGRAM}: invalid JSON: {error}\n")
    except OSError as error:
        parser.exit(2, f"{PROGRAM}: {error}\n")
    except (ValueError, KeyError, IndexError, TypeError) as error:
        parser.exit(1, f"{PROGRAM}: {error}\n")


def run() -> None:
    # zipapp's generated __main__ discards the return value, so exit explicitly.
    raise SystemExit(main())


if __name__ == "__main__":
    run()
