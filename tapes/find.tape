# find.tape — `killpy find` (locate envs that have a package installed)
# Generated: docs/gifs/find.gif
# Record via ./record.sh (isolates $HOME so only demo_projects/ appears).

Output "docs/gifs/find.gif"

Set Shell "bash"
Set Theme "Dracula"
Set FontSize 14
Set Width 1180
Set Height 560
Set Padding 18
Set TypingSpeed 65ms

Hide
Type "export HISTFILE=/dev/null PS1='$ '; clear"
Enter
Sleep 400ms
Show

# ── Scene 1: which environments have `requests` installed? ────────────────
Sleep 700ms
Type "killpy find requests --path demo_projects/high"
Sleep 900ms
Enter
Sleep 5s

# ── Scene 2: PEP 508 version specifier ────────────────────────────────────
Type "killpy find 'flask>=1.0' --path demo_projects/high"
Sleep 900ms
Enter
Sleep 5s
Sleep 2s
