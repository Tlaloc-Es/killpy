#!/bin/bash
# tester.sh – Create a rich set of fake Python environments for GIF recording.
# Usage:
#   ./tester.sh setup    – create test environments (default if no arg given)
#   ./tester.sh cleanup  – remove the demo_projects/ tree

set -euo pipefail

DEMO_ROOT="./demo_projects"

# Minimal pyvenv.cfg content that satisfies the VenvDetector
PYVENV_CFG="home = /usr/bin
include-system-site-packages = false
version = 3.12.0
executable = /usr/bin/python3
command = python3 -m venv .venv
"

create_venv() {
    local dir="$1"
    local name="${2:-.venv}"
    mkdir -p "$dir/$name/bin" "$dir/$name/lib/python3.12/site-packages"
    printf '%s' "$PYVENV_CFG" > "$dir/$name/pyvenv.cfg"
    # Add dummy installed packages to give the env a realistic size
    for pkg in requests flask numpy pandas click rich textual; do
        mkdir -p "$dir/$name/lib/python3.12/site-packages/${pkg}-1.0.dist-info"
        dd if=/dev/urandom bs=1K count=8 2>/dev/null \
            | base64 > "$dir/$name/lib/python3.12/site-packages/${pkg}/__init__.py" 2>/dev/null || true
    done
    # Fake binaries
    printf '#!/bin/sh\necho fake\n' > "$dir/$name/bin/python3"
    chmod +x "$dir/$name/bin/python3"
}

setup() {
    echo "Creating demo environments under $DEMO_ROOT …"

    # --- Flat projects (simulate ~/projects/*) ---
    local flat_projects=(
        "myapp" "api-server" "data-pipeline" "ml-experiment"
        "web-scraper" "cli-tool" "django-blog" "fastapi-demo"
        "automation" "etl-job"
    )
    for proj in "${flat_projects[@]}"; do
        create_venv "$DEMO_ROOT/flat/$proj"
    done

    # --- Nested monorepo layout ---
    local services=("auth" "users" "payments" "notifications" "reports")
    for svc in "${services[@]}"; do
        create_venv "$DEMO_ROOT/monorepo/services/$svc"
    done

    # --- Named envs (non-.venv names, detected via pyvenv.cfg) ---
    local named_envs=("venv" "env" ".env312" "py312-env" "test-env")
    for ne in "${named_envs[@]}"; do
        create_venv "$DEMO_ROOT/named_envs/$ne" "$ne"
    done

    # --- Deep nested projects ---
    create_venv "$DEMO_ROOT/org/team/backend/microservice/auth"
    create_venv "$DEMO_ROOT/org/team/backend/microservice/gateway"
    create_venv "$DEMO_ROOT/org/team/frontend/ssr-app"
    create_venv "$DEMO_ROOT/org/team/data/notebooks/analysis"
    create_venv "$DEMO_ROOT/org/team/data/pipelines/etl"

    # --- Archived / old projects ---
    local old_years=(2022 2023 2024)
    for yr in "${old_years[@]}"; do
        create_venv "$DEMO_ROOT/archive/$yr/project-alpha"
        create_venv "$DEMO_ROOT/archive/$yr/project-beta"
    done

    echo ""
    echo "Done. Created $(find "$DEMO_ROOT" -name pyvenv.cfg | wc -l) fake environments."
    echo ""
    echo "Run killpy to see the loading state:"
    echo "  killpy --path $DEMO_ROOT"
}

cleanup() {
    if [[ -d "$DEMO_ROOT" ]]; then
        rm -rf "$DEMO_ROOT"
        echo "Removed $DEMO_ROOT"
    else
        echo "$DEMO_ROOT not found, nothing to clean."
    fi
}

case "${1:-setup}" in
    setup)   setup   ;;
    cleanup) cleanup ;;
    *)
        echo "Usage: $0 [setup|cleanup]"
        exit 1
        ;;
esac
