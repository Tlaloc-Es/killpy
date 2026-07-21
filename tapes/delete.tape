# delete.tape — `killpy delete` (safe dry-run preview)
# Generated: docs/gifs/delete.gif
# Record via ./record.sh (isolates $HOME so only demo_projects/ appears).

Output "docs/gifs/delete.gif"

Set Shell "bash"
Set Theme "Dracula"
Set FontSize 14
Set Width 1200
Set Height 620
Set Padding 18
Set TypingSpeed 65ms

Hide
Type "export HISTFILE=/dev/null PS1='$ '; clear"
Enter
Sleep 400ms
Show

# ── Scene 1: preview everything with --dry-run (nothing is deleted) ───────
Sleep 700ms
Type "killpy delete --path demo_projects/high --dry-run"
Sleep 900ms
Enter
Sleep 5.5s

# ── Scene 2: scope the preview by type + age ──────────────────────────────
Type "killpy delete --path demo_projects/high --type venv --older-than 365 --dry-run"
Sleep 900ms
Enter
Sleep 5s
Sleep 2s
