# clean.tape — `killpy clean` (remove __pycache__ dirs)
# Generated: docs/gifs/clean.gif
# Record via ./record.sh (isolates $HOME so only demo_projects/ appears).

Output "docs/gifs/clean.gif"

Set Shell "bash"
Set Theme "Dracula"
Set FontSize 14
Set Width 1120
Set Height 520
Set Padding 18
Set TypingSpeed 65ms

Hide
Type "export HISTFILE=/dev/null PS1='$ '; clear"
Enter
Sleep 300ms
# Seed a few __pycache__ dirs so the demo has something to remove.
Type "mkdir -p demo_projects/pkg/__pycache__ demo_projects/pkg/sub/__pycache__"
Enter
Type "echo stub > demo_projects/pkg/__pycache__/mod.cpython-312.pyc"
Enter
Type "clear"
Enter
Sleep 200ms
Show

# ── Scene 1: caches present before cleaning ───────────────────────────────
Sleep 700ms
Type "find demo_projects -type d -name __pycache__"
Sleep 900ms
Enter
Sleep 3.5s

# ── Scene 2: run clean ────────────────────────────────────────────────────
Type "killpy clean --path demo_projects"
Sleep 900ms
Enter
Sleep 3.5s

# ── Scene 3: gone ─────────────────────────────────────────────────────────
Type "find demo_projects -type d -name __pycache__"
Sleep 900ms
Enter
Sleep 3s
Sleep 2s
