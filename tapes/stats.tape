# stats.tape — `killpy stats` (disk usage grouped by type)
# Generated: docs/gifs/stats.gif
# Record via ./record.sh (isolates $HOME so only demo_projects/ appears).

Output "docs/gifs/stats.gif"

Set Shell "bash"
Set Theme "Dracula"
Set FontSize 14
Set Width 1120
Set Height 560
Set Padding 18
Set TypingSpeed 65ms

Hide
Type "export HISTFILE=/dev/null PS1='$ '; clear"
Enter
Sleep 400ms
Show

# ── Scene 1: the summary table ────────────────────────────────────────────
Sleep 700ms
Type "killpy stats --path demo_projects"
Sleep 900ms
Enter
Sleep 5s

# ── Scene 2: machine-readable JSON ────────────────────────────────────────
Type "killpy stats --path demo_projects --json | head -20"
Sleep 900ms
Enter
Sleep 5s
Sleep 2s
