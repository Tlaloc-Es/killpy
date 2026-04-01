# Contributing to killpy

Thank you for wanting to improve killpy! Contributions of all kinds are welcome — bug reports, feature ideas, documentation fixes, and pull requests.

______________________________________________________________________

## Quick start

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/<your-username>/killpy.git
cd killpy

# 2. Install with development dependencies (uv recommended)
pip install -e ".[dev]"
# or
uv sync

# 3. Verify everything works
python -m compileall killpy
pytest tests/
```

______________________________________________________________________

## Development workflow

1. **Create a branch** off `master` (or `main`):
   ```bash
   git checkout -b feat/my-feature
   ```
1. **Make focused, minimal changes** — avoid refactoring unrelated code.
1. **Run tests** before committing:
   ```bash
   pytest tests/
   ```
1. **Run the linter / type checker** if available:
   ```bash
   ruff check killpy
   mypy killpy
   ```
1. **Write a commit message** following [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat: add --exclude option to skip path patterns
   fix: handle missing conda command gracefully
   docs: update keybindings table in README
   ```
1. **Open a pull request** against `master` with a clear description of *what* and *why*.

______________________________________________________________________

## Adding a new detector

Detectors live in `killpy/detectors/`. Each one inherits from `AbstractDetector` in `base.py`.

```python
from killpy.detectors.base import AbstractDetector
from killpy.models import Environment

class MyToolDetector(AbstractDetector):
    name = "mytool"

    def detect(self, path: Path) -> list[Environment]:
        # return a list of Environment objects
        ...
```

Then register it in `killpy/scanner.py` inside `_build_detectors()`.

______________________________________________________________________

## Recording a demo GIF

A compelling demo GIF is one of the best ways to showcase new features.

**Recommended setup:**

- Terminal: 100 × 30 characters, dark theme
- Tool: [vhs](https://github.com/charmbracelet/vhs) or [asciinema](https://asciinema.org/) + [agg](https://github.com/asciinema/agg)
- Content: show scanning, filtering with `/`, multi-selecting with `T`/`Space`, and deleting

Update `show.gif` in the repo root and reference it in `README.md`.

______________________________________________________________________

## Good first issues

Look for issues labelled [`good first issue`](https://github.com/Tlaloc-Es/killpy/labels/good%20first%20issue) — these are intentionally scoped to be approachable for new contributors.

______________________________________________________________________

## Code of conduct

Be respectful and constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).
