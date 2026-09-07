#!/bin/sh
# Download bunmyaku and delegate installation to its Python installer.

bunmyaku_install() (
    set -eu
    command -v curl >/dev/null 2>&1 || {
        printf '%s\n' 'curl is required.' >&2
        exit 1
    }
    python_command=
    for candidate in python3 python py; do
        if command -v "$candidate" >/dev/null 2>&1 &&
            "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' </dev/null 2>/dev/null; then
            python_command=$candidate
            break
        fi
    done
    if [ -z "$python_command" ]; then
        printf '%s\n' 'Python 3.11 or newer is required. Install Python, then run this command again.' >&2
        exit 1
    fi
    temporary=$(mktemp -d "${TMPDIR:-/tmp}/bunmyaku.XXXXXXXX")
    trap 'rm -rf -- "$temporary"' 0
    trap 'exit 129' HUP
    trap 'exit 130' INT
    trap 'exit 143' TERM
    printf '%s\n' 'Downloading bunmyaku from github.com/kathoc/bunmyaku ...'
    curl --fail --silent --show-error --location \
        --proto '=https' --proto-redir '=https' \
        --connect-timeout 15 --max-time 180 --retry 2 \
        'https://github.com/kathoc/bunmyaku/archive/refs/heads/main.zip' \
        --output "$temporary/source.zip"
    "$python_command" - "$temporary" "$@" <<'PY'
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

# Git Bash uses POSIX paths, while a Windows Python uses native paths.
temporary = sys.argv[1]
if os.name == "nt":
    temporary = subprocess.check_output(["cygpath", "-w", temporary], text=True).strip()
root = Path(temporary)
destination = root / "source"
prefix = "bunmyaku-main/"
with zipfile.ZipFile(root / "source.zip") as archive:
    selected = []
    seen = set()
    total = 0
    for entry in archive.infolist():
        if entry.is_dir() or not entry.filename.startswith(prefix):
            continue
        name = entry.filename[len(prefix):]
        if name != "install.py" and not name.startswith("src/jlangbase/"):
            continue
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
            raise SystemExit("Unsafe archive path")
        if (entry.external_attr >> 16) & 0o170000 == 0o120000:
            raise SystemExit("Archive symlinks are not supported")
        if name in seen:
            raise SystemExit("Duplicate archive entry")
        seen.add(name)
        total += entry.file_size
        if total > 64 * 1024 * 1024 or len(seen) > 4096:
            raise SystemExit("Archive exceeds installation limits")
        selected.append((entry, path))
    if not {"install.py", "src/jlangbase/distribution.py"} <= seen:
        raise SystemExit("Archive is missing the installer")
    for entry, path in selected:
        target = destination.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(archive.read(entry))
result = subprocess.run(
    [sys.executable, str(destination / "install.py"), *sys.argv[2:]],
    stdin=subprocess.DEVNULL,
)
raise SystemExit(result.returncode)
PY
)

bunmyaku_install "$@"
