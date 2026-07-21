#!/usr/bin/env bash
# record.sh — generate every killpy README GIF with vhs.
#
# It creates the demo environments once, records each tape into docs/gifs/,
# and removes the demo data afterwards. Each tape is fast because it no longer
# builds its own fixtures — that happens here, a single time.
#
# Usage:
#   ./record.sh                    # record every tape
#   ./record.sh tapes/list.tape    # record only the given tape(s)
#
# Requires: vhs (https://github.com/charmbracelet/vhs), ttyd, ffmpeg and a
# `killpy` on PATH (a local .venv/ is used automatically if present).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GIF_DIR="docs/gifs"
ALL_TAPES=(
    tapes/demo.tape
    tapes/list.tape
    tapes/list-json.tape
    tapes/find.tape
    tapes/stats.tape
    tapes/delete.tape
    tapes/clean.tape
    tapes/doctor.tape
)
TAPES=("${@:-${ALL_TAPES[@]}}")

# --- Preconditions --------------------------------------------------------
command -v vhs >/dev/null 2>&1 || {
    echo "✗ vhs not found — install it: https://github.com/charmbracelet/vhs"
    exit 1
}

# Prefer the local dev install so the tapes can just call `killpy`.
if [[ -x .venv/bin/killpy ]]; then
    export PATH="$SCRIPT_DIR/.venv/bin:$PATH"
fi
command -v killpy >/dev/null 2>&1 || {
    echo "✗ killpy not on PATH — install it (pipx/uv tool) or create a .venv"
    exit 1
}

# --- Isolated HOME --------------------------------------------------------
# The global detectors (uv tools/pythons, pipx, poetry, pyenv, hatch, pipenv,
# global caches) intentionally ignore --path and read from $HOME. Without
# isolation they would inject the *recording machine's real environments*
# (and their names) into every GIF. Point HOME at a throwaway empty dir so the
# GIFs show only the demo_projects/ fixtures.
REC_HOME="$(mktemp -d)"

# --- Demo fixtures (created once, cleaned on exit) ------------------------
cleanup() {
    echo "→ Removing demo environments…"
    bash tester.sh cleanup >/dev/null 2>&1 || true
    rm -rf "$REC_HOME" 2>/dev/null || true
}
trap cleanup EXIT

mkdir -p "$GIF_DIR"

# From here on, every `killpy` invoked inside a tape sees the clean HOME.
# Seed a minimal rc so the recorded shell keeps killpy on PATH and a clean
# prompt regardless of how vhs starts bash.
KILLPY_BIN="$SCRIPT_DIR/.venv/bin"
[[ -x "$KILLPY_BIN/killpy" ]] || KILLPY_BIN="$(dirname "$(command -v killpy)")"
cat > "$REC_HOME/.bashrc" <<RC
export PATH="$KILLPY_BIN:\$PATH"
export PS1='\$ '
export HISTFILE=/dev/null
RC
cp "$REC_HOME/.bashrc" "$REC_HOME/.bash_profile"
export HOME="$REC_HOME"

# --- Record ---------------------------------------------------------------
# Fixtures are re-created before EVERY tape. This is not just tidiness: the
# demo (TUI) tape performs a real delete, so a single shared fixture set would
# leave every tape recorded after it with fewer environments. A fresh set per
# tape guarantees each GIF shows the full, identical scenario.
echo ""
echo "→ Recording ${#TAPES[@]} tape(s) into $GIF_DIR/ …"
echo ""

failed=()
for tape in "${TAPES[@]}"; do
    if [[ ! -f "$tape" ]]; then
        echo "  ✗ Not found: $tape"
        failed+=("$tape")
        continue
    fi
    bash tester.sh cleanup >/dev/null 2>&1 || true
    bash tester.sh setup >/dev/null
    echo "  • vhs $tape"
    if vhs "$tape" >/dev/null 2>&1; then
        echo "    ✓ OK"
    else
        echo "    ✗ Failed: $tape"
        failed+=("$tape")
    fi
done

echo ""
if [[ ${#failed[@]} -eq 0 ]]; then
    echo "✓ All GIFs generated in $GIF_DIR/"
    ls -lh "$GIF_DIR"/*.gif 2>/dev/null || true
else
    echo "⚠ Completed with ${#failed[@]} error(s):"
    for f in "${failed[@]}"; do echo "  - $f"; done
    exit 1
fi
