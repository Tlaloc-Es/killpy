# list.tape — `killpy list` (inspect environments)
# Generated: docs/gifs/list.gif
# Record via ./record.sh (isolates $HOME so only demo_projects/ appears).

Output "docs/gifs/list.gif"

Set Shell "bash"
Set Theme "Dracula"
Set FontSize 14
Set Width 1180
Set Height 780
Set Padding 18
Set TypingSpeed 65ms

Hide
Type "export HISTFILE=/dev/null PS1='$ '; clear"
Enter
Sleep 400ms
Show

# ── Scene 1: list every environment ───────────────────────────────────────
Sleep 700ms
Type "killpy list --path demo_projects"
Sleep 900ms
Enter
Sleep 6s

# ── Scene 2: only the ones untouched for over a year ──────────────────────
Type "killpy list --path demo_projects --older-than 365"
Sleep 900ms
Enter
Sleep 5s
Sleep 2s
