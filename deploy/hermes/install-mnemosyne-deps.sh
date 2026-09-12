#!/bin/bash
# s6 cont-init, before Gateway starts. Never hot-install into a running Gateway.
set -euo pipefail
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON="${MNEMOSYNE_DEPS_PYTHON:-/opt/hermes/.venv/bin/python3}"
UV="${MNEMOSYNE_DEPS_UV:-/usr/local/bin/uv}"
LOCK="${MNEMOSYNE_DEPS_LOCK:-${SCRIPT_DIR}/mnemosyne-deps.lock}"
INDEX="${MNEMOSYNE_DEPS_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"

[ -x "$PYTHON" ] || { echo "Missing Python: $PYTHON" >&2; exit 1; }
[ -f "$LOCK" ] || { echo "Missing dependency lock: $LOCK" >&2; exit 1; }
# Hard guard before any installer can touch the shared venv.
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 13) else "This lock requires Python 3.13; revalidate before upgrading")'

check_deps() {
    "$PYTHON" - "$LOCK" <<'PY'
import importlib.metadata as metadata
from pathlib import Path
import re, sqlite3, sys
for name, expected in re.findall(r'^([A-Za-z0-9_.-]+)==([^\s\\]+)', Path(sys.argv[1]).read_text(), re.M):
    actual = metadata.version(name)
    if actual != expected:
        raise SystemExit(f'{name}: expected {expected}, got {actual}')
import yaml, fastembed, numpy, sqlite_vec
with sqlite3.connect(':memory:') as conn:
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute('CREATE VIRTUAL TABLE smoke_vec USING vec0(embedding float[4])')
    conn.execute('CREATE VIRTUAL TABLE smoke_fts USING fts5(content)')
print('Mnemosyne locked dependencies and SQLite extensions: OK')
PY
}

if check_deps; then
    exit 0
fi
[ -x "$UV" ] || { echo "Missing uv: $UV" >&2; exit 1; }
# install, not sync: preserve unrelated Hermes packages in the shared venv.
"$UV" --no-config pip install --python "$PYTHON" --index-url "$INDEX" --require-hashes -r "$LOCK"
check_deps
