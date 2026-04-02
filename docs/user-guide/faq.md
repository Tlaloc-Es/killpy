# FAQ

## What is `killpy`?

`killpy` is a Python CLI and Textual TUI for finding, inspecting, and removing unused Python environments and related disk usage.

## Can `killpy` find old virtual environments?

Yes. It detects local `.venv` directories and directories containing `pyvenv.cfg`, which covers common virtual environment layouts.

## Can `killpy` delete Conda environments?

Yes. For Conda-managed environments, deletion goes through the Conda command line rather than direct filesystem deletion.

## Can `killpy` inspect Poetry environments?

Yes. It detects Poetry virtual environments stored in Poetry's cache directory.

## Can `killpy` inspect `pipx` package size?

Yes. It detects `pipx` packages through `pipx list --json` and computes their environment size.

## Does the TUI show caches and artifacts?

Not today. The TUI renders environment results and a dedicated `pipx` tab. Cache and artifact detection currently exist in scanner and CLI flows.

## What does `killpy clean` remove?

`killpy clean` removes `__pycache__` directories recursively under the selected path. It is narrower than the full cache detector model.

## Is `killpy` safe to use?

`killpy` does not delete anything just by scanning. The TUI requires explicit actions, and tool-managed environments use the owning tool when possible.

## Is `killpy` useful for CI or automation?

Yes. The `list`, `delete`, and `stats` commands support non-interactive usage, and `list` can emit JSON or NDJSON.

## Where is the source code?

The GitHub repository is [Tlaloc-Es/killpy](https://github.com/Tlaloc-Es/killpy).
