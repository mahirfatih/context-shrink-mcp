#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_LINT=1
RUN_TESTS=1
INSTALL=1
TARGETS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --unit)
            TARGETS+=("test/py/context-shrink-tests.py")
            ;;
        --integration)
            TARGETS+=("test/py/context-shrink-live-tests.py")
            ;;
        --e2e)
            TARGETS+=("test/py/context-shrink-mcp-tests.py")
            ;;
        --smoke|--sanity)
            TARGETS+=("test/py/context-shrink-tests.py" "test/py/context-shrink-mcp-tests.py")
            ;;
        --regression)
            TARGETS+=("test/py/context-shrink-tests.py" "test/py/context-shrink-mcp-tests.py")
            ;;
        --lint) RUN_TESTS=0 ;;
        --no-install) INSTALL=0 ;;
        --only) shift; TARGETS+=("${1:-}") ;;
        -h|--help) sed -n '1,25p' "$0"; exit 0 ;;
        *) echo "unknown flag: $1" >&2; exit 2 ;;
    esac
    shift
done

if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PY=("$ROOT/.venv/bin/python")
else
    PY=("${PYTHON:-python3}")
fi

if [[ "$INSTALL" == 1 ]]; then
    echo "== install =="
    "${PY[@]}" -m pip install -q -r requirements-dev.txt
fi
if [[ "$RUN_LINT" == 1 ]]; then
    echo "== ruff =="
    "${PY[@]}" -m ruff check .
fi
if [[ "$RUN_TESTS" == 1 ]]; then
    echo "== pytest =="
    if [[ ${#TARGETS[@]} -gt 0 ]]; then
        "${PY[@]}" -m pytest -q "${TARGETS[@]}"
    else
        "${PY[@]}" -m pytest -q
    fi
fi
echo "== smoke =="
"${PY[@]}" context-shrink.py --help >/dev/null && echo "server CLI ok"