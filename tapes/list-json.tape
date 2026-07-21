# list-json.tape — `killpy list --json` + jq / NDJSON pipelines
# Generated: docs/gifs/list-json.gif
# Record via ./record.sh (isolates $HOME so only demo_projects/ appears).

Output "docs/gifs/list-json.gif"

Set Shell "bash"
Set Theme "Dracula"
Set FontSize 14
Set Width 1240
Set Height 540
Set Padding 18
Set TypingSpeed 60ms

Hide
Type "export HISTFILE=/dev/null PS1='$ '; clear"
Enter
Sleep 400ms
Show

# ── Scene 1: type + human size of each env, via jq ────────────────────────
Sleep 700ms
Type "killpy list --path demo_projects --json --quiet | jq -c '.[] | {name, size_human}' | head -6"
Sleep 900ms
Enter
Sleep 5s

# ── Scene 2: NDJSON stream — one env per line ─────────────────────────────
Type "killpy list --path demo_projects --json-stream --quiet | head -3"
Sleep 900ms
Enter
Sleep 5s
Sleep 2s
