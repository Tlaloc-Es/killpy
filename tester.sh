#!/bin/bash
# tester.sh – Create fake Python environments covering all doctor scoring cases.
#
# Scenarios created:
#   HIGH   – orphan (no project files) + old timestamp  →  safe to delete
#   MEDIUM – project files present but env is 3-6 months old  →  review
#   LOW    – recent env inside an active project  →  keep
#   LARGE  – big orphan env (extra disk weight)
#   SMART  – mix of nested / named / monorepo envs for general UI testing
#
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# create_venv DIR [ENV_NAME] [PKG_COUNT] [PKG_SIZE_KB]
create_venv() {
    local dir="$1"
    local name="${2:-.venv}"
    local pkg_count="${3:-5}"
    local pkg_size_kb="${4:-8}"
    local env_path="$dir/$name"

    mkdir -p "$env_path/bin" "$env_path/lib/python3.12/site-packages"
    printf '%s' "$PYVENV_CFG" > "$env_path/pyvenv.cfg"

    local pkgs=(requests flask numpy pandas click rich textual django fastapi sqlalchemy)
    for i in $(seq 0 $((pkg_count - 1))); do
        local pkg="${pkgs[$((i % ${#pkgs[@]}))]}"
        mkdir -p "$env_path/lib/python3.12/site-packages/${pkg}-1.0.dist-info"
        dd if=/dev/urandom bs=1K count="$pkg_size_kb" 2>/dev/null \
            | base64 > "$env_path/lib/python3.12/site-packages/${pkg}/__init__.py" 2>/dev/null || true
    done

    printf '#!/bin/sh\necho fake\n' > "$env_path/bin/python3"
    chmod +x "$env_path/bin/python3"
}

# age_dir DIR DAYS  – back-date the mtime of DIR and all its contents
age_dir() {
    local dir="$1"
    local days="$2"
    find "$dir" -exec touch -d "${days} days ago" {} \; 2>/dev/null || true
}

# write_project_file DIR FILE – create a project marker file so orphan detection passes
write_project_file() {
    local dir="$1"
    local file="${2:-pyproject.toml}"
    printf '[project]\nname = "demo"\nversion = "0.1.0"\n' > "$dir/$file"
}

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

setup() {
    echo "Creating demo environments under $DEMO_ROOT …"
    echo ""

    # -----------------------------------------------------------------------
    # HIGH: orphan envs with no project files, old timestamps
    # Expected score: high (orphan=1.0, age≥180d)
    # -----------------------------------------------------------------------
    echo "  [HIGH] Orphan environments (>6 months old, no project files)…"

    create_venv "$DEMO_ROOT/high/abandoned-ml-experiment"  ".venv" 7 12
    age_dir     "$DEMO_ROOT/high/abandoned-ml-experiment"  500

    create_venv "$DEMO_ROOT/high/old-poc"                  ".venv" 4 10
    age_dir     "$DEMO_ROOT/high/old-poc"                  730

    create_venv "$DEMO_ROOT/high/stale-scraper"            ".venv" 3 8
    age_dir     "$DEMO_ROOT/high/stale-scraper"            400

    create_venv "$DEMO_ROOT/high/forgotten-prototype"      ".venv" 6 15
    age_dir     "$DEMO_ROOT/high/forgotten-prototype"      600

    create_venv "$DEMO_ROOT/high/temp-analysis"            "venv"  5 10
    age_dir     "$DEMO_ROOT/high/temp-analysis"            365

    # -----------------------------------------------------------------------
    # HIGH: large orphan env (extra disk weight)
    # Expected score: high (orphan=1.0, large size, old)
    # -----------------------------------------------------------------------
    echo "  [HIGH] Large orphan environment (data-science stack)…"

    create_venv "$DEMO_ROOT/high/heavy-datascience"        ".venv" 10 200
    age_dir     "$DEMO_ROOT/high/heavy-datascience"        450

    # -----------------------------------------------------------------------
    # MEDIUM: envs inside projects (project file present) but 3-6 months old
    # Expected score: medium (age 90-180d, not orphan)
    # -----------------------------------------------------------------------
    echo "  [MEDIUM] Project envs that are 3-6 months old…"

    create_venv "$DEMO_ROOT/medium/api-v1"                 ".venv" 5 8
    write_project_file "$DEMO_ROOT/medium/api-v1"          "pyproject.toml"
    age_dir     "$DEMO_ROOT/medium/api-v1"                 120

    create_venv "$DEMO_ROOT/medium/legacy-service"         ".venv" 6 10
    write_project_file "$DEMO_ROOT/medium/legacy-service"  "requirements.txt"
    age_dir     "$DEMO_ROOT/medium/legacy-service"         150

    create_venv "$DEMO_ROOT/medium/migration-tool"         ".venv" 4 8
    write_project_file "$DEMO_ROOT/medium/migration-tool"  "setup.py"
    age_dir     "$DEMO_ROOT/medium/migration-tool"         100

    create_venv "$DEMO_ROOT/medium/data-pipeline"          ".venv" 5 12
    write_project_file "$DEMO_ROOT/medium/data-pipeline"   "pyproject.toml"
    age_dir     "$DEMO_ROOT/medium/data-pipeline"          180

    # -----------------------------------------------------------------------
    # LOW: recently used envs inside active projects
    # Expected score: low (active use, not orphan, small age)
    # -----------------------------------------------------------------------
    echo "  [LOW] Active project environments (recently used)…"

    create_venv "$DEMO_ROOT/low/current-webapp"            ".venv" 6 8
    write_project_file "$DEMO_ROOT/low/current-webapp"     "pyproject.toml"
    age_dir     "$DEMO_ROOT/low/current-webapp"            5

    create_venv "$DEMO_ROOT/low/active-api"                ".venv" 5 10
    write_project_file "$DEMO_ROOT/low/active-api"         "pyproject.toml"
    age_dir     "$DEMO_ROOT/low/active-api"                10

    create_venv "$DEMO_ROOT/low/fresh-experiment"          ".venv" 3 6
    write_project_file "$DEMO_ROOT/low/fresh-experiment"   "requirements.txt"
    age_dir     "$DEMO_ROOT/low/fresh-experiment"          2

    create_venv "$DEMO_ROOT/low/daily-scripts"             ".venv" 4 5
    write_project_file "$DEMO_ROOT/low/daily-scripts"      "setup.py"
    age_dir     "$DEMO_ROOT/low/daily-scripts"             1

    # -----------------------------------------------------------------------
    # SMART: mixed / nested layouts for general UI + list testing
    # -----------------------------------------------------------------------
    echo "  [SMART] Mixed layouts for general UI testing…"

    local flat_projects=("myapp" "api-server" "cli-tool" "django-blog" "fastapi-demo")
    for proj in "${flat_projects[@]}"; do
        create_venv "$DEMO_ROOT/smart/flat/$proj"
        write_project_file "$DEMO_ROOT/smart/flat/$proj" "pyproject.toml"
    done

    local services=("auth" "users" "payments" "notifications")
    for svc in "${services[@]}"; do
        create_venv "$DEMO_ROOT/smart/monorepo/services/$svc"
        write_project_file "$DEMO_ROOT/smart/monorepo/services/$svc" "pyproject.toml"
    done
    age_dir "$DEMO_ROOT/smart/monorepo" 90

    local named_envs=("venv" "env" ".env312" "py312-env")
    for ne in "${named_envs[@]}"; do
        create_venv "$DEMO_ROOT/smart/named_envs/$ne" "$ne"
    done
    age_dir "$DEMO_ROOT/smart/named_envs" 200

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    local total
    total=$(find "$DEMO_ROOT" -name pyvenv.cfg | wc -l)
    echo ""
    echo "Done. Created $total fake environments."
    echo ""
    echo "  HIGH  (orphan / old):    $(find "$DEMO_ROOT/high"   -name pyvenv.cfg 2>/dev/null | wc -l)"
    echo "  MEDIUM (project / aged): $(find "$DEMO_ROOT/medium" -name pyvenv.cfg 2>/dev/null | wc -l)"
    echo "  LOW   (active project):  $(find "$DEMO_ROOT/low"    -name pyvenv.cfg 2>/dev/null | wc -l)"
    echo "  SMART (UI / general):    $(find "$DEMO_ROOT/smart"  -name pyvenv.cfg 2>/dev/null | wc -l)"
    echo ""
    echo "Commands to try:"
    echo "  killpy --path $DEMO_ROOT"
    echo "  killpy doctor --path $DEMO_ROOT"
    echo "  killpy doctor --path $DEMO_ROOT --all"
    echo "  killpy list   --path $DEMO_ROOT --json"
    echo "  killpy stats  --path $DEMO_ROOT"
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
