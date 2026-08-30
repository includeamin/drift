#!/usr/bin/env bash
#
# Installer and updater for the `jdiff` command.
#
# The project has no runtime dependencies, so jdiff ships as a zipapp (PEP 441):
# a single self-contained executable that starts as fast as a plain script.
#
# Remote install (no clone required):
#   curl -fsSL https://raw.githubusercontent.com/includeamin/diff/main/install.sh | bash
#
# Usage:
#   bash install.sh                  Install or reinstall the latest release
#   bash install.sh --check          Report whether a newer release exists
#   bash install.sh --update         Install only if a newer release exists
#   bash install.sh --ref v0.5.0     Install a specific tag, branch or commit
#   bash install.sh --local          Build from the working tree instead of GitHub
#   bash install.sh --uninstall      Remove jdiff and its cached checkout
#
# Environment:
#   PREFIX    Install prefix (default: ~/.local)
#   BIN_DIR   Executable directory (default: $PREFIX/bin)
#   REPO_URL  Override the source repository
#
set -euo pipefail

readonly PROGRAM="jdiff"
readonly REPO_SLUG="includeamin/diff"
readonly MIN_MAJOR=3
readonly MIN_MINOR=11

REPO_URL="${REPO_URL:-https://github.com/${REPO_SLUG}.git}"
PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="${BIN_DIR:-$PREFIX/bin}"
DATA_DIR="${DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/$PROGRAM}"

TARGET="$BIN_DIR/$PROGRAM"
MANIFEST="$DATA_DIR/manifest"
CHECKOUT="$DATA_DIR/checkout"

MODE="install"
REQUESTED_REF=""
USE_LOCAL=0
SOURCE_ROOT=""
RESOLVED_REF=""

info() { printf '\033[36m==>\033[0m %s\n' "$*"; }
ok() { printf '\033[32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33mwarning:\033[0m %s\n' "$*" >&2; }
die() {
    printf '\033[31merror:\033[0m %s\n' "$*" >&2
    exit 1
}

usage() {
    sed -n '3,23p' "${BASH_SOURCE[0]}" | sed 's/^#\{1\} \{0,1\}//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --check) MODE="check" ;;
        --update) MODE="update" ;;
        --uninstall) MODE="uninstall" ;;
        --local) USE_LOCAL=1 ;;
        --ref)
            [[ $# -ge 2 ]] || die "--ref requires a value"
            REQUESTED_REF="$2"
            shift
            ;;
        --ref=*) REQUESTED_REF="${1#*=}" ;;
        -h | --help) usage ;;
        *) die "Unknown option: $1 (try --help)" ;;
    esac
    shift
done

require() { command -v "$1" >/dev/null 2>&1 || die "'$1' is required but was not found on PATH."; }

find_python() {
    local candidate
    for candidate in python3.14 python3.13 python3.12 python3.11 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 &&
            "$candidate" -c "import sys; sys.exit(0 if sys.version_info[:2] >= ($MIN_MAJOR, $MIN_MINOR) else 1)" 2>/dev/null; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

# Resolved without the GitHub API so there is no rate limit and no jq dependency.
latest_tag() {
    git ls-remote --tags --refs --sort=-v:refname "$REPO_URL" 'v*' 2>/dev/null |
        head -n1 | sed 's#.*refs/tags/##'
}

installed_version() {
    [[ -f "$MANIFEST" ]] || return 1
    local value
    value="$(sed -n 's/^version=//p' "$MANIFEST" | head -n1)"
    [[ -n "$value" ]] || return 1
    printf '%s\n' "$value"
}

# Returns 0 when $1 is strictly newer than $2.
version_gt() {
    local a="${1#v}" b="${2#v}"
    [[ "$a" != "$b" ]] && [[ "$(printf '%s\n%s\n' "$a" "$b" | sort -V | tail -n1)" == "$a" ]]
}

uninstall() {
    local removed=0
    if [[ -e "$TARGET" ]]; then
        rm -f "$TARGET"
        ok "Removed $TARGET"
        removed=1
    fi
    if [[ -d "$DATA_DIR" ]]; then
        rm -rf "$DATA_DIR"
        ok "Removed $DATA_DIR"
        removed=1
    fi
    [[ $removed -eq 1 ]] || info "$PROGRAM is not installed."
    exit 0
}

# Exits 0 when up to date, 10 when an update is available.
check_for_update() {
    require git
    local current latest
    current="$(installed_version || true)"
    latest="$(latest_tag)"

    [[ -n "$latest" ]] || die "Could not determine the latest release from $REPO_URL"

    if [[ -z "$current" ]]; then
        info "$PROGRAM is not installed. Latest release is $latest."
        return 10
    fi

    info "Installed: $current"
    info "Latest:    $latest"

    if version_gt "$latest" "$current"; then
        ok "An update is available: $current -> $latest"
        return 10
    fi

    ok "$PROGRAM is up to date."
    return 0
}

# Populates SOURCE_ROOT with a directory containing the src/diff package.
fetch_source() {
    if [[ $USE_LOCAL -eq 1 ]]; then
        local here
        here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        [[ -d "$here/src/diff" ]] || die "--local requires running from inside the repository."
        SOURCE_ROOT="$here"
        RESOLVED_REF="local"
        return
    fi

    require git
    local ref="$REQUESTED_REF"
    if [[ -z "$ref" ]]; then
        ref="$(latest_tag)"
        [[ -n "$ref" ]] || die "No release tags found in $REPO_URL"
    fi

    info "Fetching $REPO_SLUG at $ref..."
    rm -rf "$CHECKOUT"
    mkdir -p "$(dirname "$CHECKOUT")"

    if ! git clone --quiet --depth 1 --branch "$ref" "$REPO_URL" "$CHECKOUT" 2>/dev/null; then
        # --branch only accepts tags and branches, so fall back for raw commits.
        git clone --quiet "$REPO_URL" "$CHECKOUT" || die "Failed to clone $REPO_URL"
        git -C "$CHECKOUT" checkout --quiet "$ref" || die "Unknown ref: $ref"
    fi

    [[ -d "$CHECKOUT/src/diff" ]] || die "The checkout at $ref does not contain src/diff."
    SOURCE_ROOT="$CHECKOUT"
    RESOLVED_REF="$ref"
}

build_and_install() {
    local python package_version staging recorded
    python="$(find_python)" ||
        die "Python ${MIN_MAJOR}.${MIN_MINOR}+ is required but was not found on PATH."
    info "Using interpreter: $python ($("$python" -c 'import platform; print(platform.python_version())'))"

    mkdir -p "$BIN_DIR" "$DATA_DIR"

    # Stage only the runtime package so caches and tests stay out of the archive.
    staging="$(mktemp -d)"
    trap 'rm -rf "$staging"' RETURN

    cp -R "$SOURCE_ROOT/src/diff" "$staging/diff"
    find "$staging" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true

    info "Building zipapp..."
    "$python" -m zipapp "$staging" \
        --main "diff.cli:run" \
        --python "/usr/bin/env $(basename "$python")" \
        --compress \
        --output "$staging/$PROGRAM"
    chmod +x "$staging/$PROGRAM"

    # Verify before touching the installed copy, so a bad build never replaces
    # a working one.
    if ! "$staging/$PROGRAM" --version >/dev/null 2>&1; then
        die "The build at ${RESOLVED_REF} is not a working $PROGRAM executable."
    fi

    mv -f "$staging/$PROGRAM" "$TARGET"
    chmod +x "$TARGET"

    package_version="$("$python" -c "
import pathlib, re, sys
text = pathlib.Path(sys.argv[1], 'diff', '__init__.py').read_text(encoding='utf-8')
match = re.search(r'__version__\s*=\s*\"([^\"]+)\"', text)
print(match.group(1) if match else 'unknown')
" "$SOURCE_ROOT/src")"

    recorded="$RESOLVED_REF"
    [[ "$recorded" == "local" ]] && recorded="v${package_version}+local"

    {
        echo "version=$recorded"
        echo "package_version=$package_version"
        echo "installed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "path=$TARGET"
        echo "repo=$REPO_URL"
    } > "$MANIFEST"

    ok "Installed $PROGRAM $recorded -> $TARGET"
}

warn_if_not_on_path() {
    case ":${PATH}:" in
        *":$BIN_DIR:"*) ;;
        *)
            warn "$BIN_DIR is not on your PATH. Add it with:"
            printf '\n  bash/zsh:  echo '\''export PATH="%s:$PATH"'\'' >> ~/.bashrc\n' "$BIN_DIR"
            printf '  fish:      fish_add_path %s\n\n' "$BIN_DIR"
            ;;
    esac
}

case "$MODE" in
    uninstall)
        uninstall
        ;;
    check)
        set +e
        check_for_update
        status=$?
        set -e
        [[ $status -eq 10 ]] && exit 10
        exit $status
        ;;
    update)
        if [[ $USE_LOCAL -eq 0 && -z "$REQUESTED_REF" ]]; then
            set +e
            check_for_update
            status=$?
            set -e
            [[ $status -eq 0 ]] && exit 0
            [[ $status -eq 10 ]] || exit $status
        fi
        fetch_source
        build_and_install
        ;;
    install)
        fetch_source
        build_and_install
        warn_if_not_on_path
        info "Try it:  $PROGRAM --help"
        ;;
esac
