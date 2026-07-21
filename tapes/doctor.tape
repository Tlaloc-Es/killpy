# doctor.tape — `killpy doctor` (smart health report)
# Generated: docs/gifs/doctor.gif
# Record via ./record.sh (isolates $HOME so only demo_projects/ appears).

Output "docs/gifs/doctor.gif"

Set Shell "bash"
Set Theme "Dracula"
Set FontSize 14
Set Width 1240
Set Height 720
Set Padding 18
Set TypingSpeed 65ms

Hide
Type "export HISTFILE=/dev/null PS1='$ '; clear"
Enter
Sleep 400ms
Show

# ── Scene 1: top offenders (default) ──────────────────────────────────────
Sleep 700ms
Type "killpy doctor --path demo_projects"
Sleep 900ms
Enter
Sleep 6.5s

# ── Scene 2: full report grouped by category (scoped so it fits) ──────────
Type "killpy doctor --path demo_projects/medium --all"
Sleep 900ms
Enter
Sleep 6s
Sleep 2s
