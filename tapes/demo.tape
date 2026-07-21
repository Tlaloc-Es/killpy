# demo.tape — killpy interactive TUI (README hero GIF)
# Generated: docs/gifs/demo.gif
# Record via ./record.sh (it runs `tester.sh setup` once and isolates $HOME so
# only the demo_projects/ fixtures appear — never the recording machine's real
# environments). Standalone: `bash tester.sh setup` first, but real envs leak.

Output "docs/gifs/demo.gif"

Set Shell "bash"
Set Theme "Dracula"
Set FontSize 13
Set Width 1280
Set Height 720
Set Padding 20
Set TypingSpeed 70ms
Set PlaybackSpeed 0.9

# ── silent prompt reset ───────────────────────────────────────────────────
Hide
Type "export HISTFILE=/dev/null PS1='$ '; clear"
Enter
Sleep 500ms
Show

# ── Scene 1: launch the TUI ───────────────────────────────────────────────
Sleep 800ms
Type "killpy --path demo_projects"
Sleep 1.2s
Enter
# let the table stream in and settle
Sleep 6s

# ── Scene 2: browse — HIGH / MED / LOW health colouring ───────────────────
Down
Sleep 600ms
Down
Sleep 600ms
Down
Sleep 600ms
Down
Sleep 800ms
Up
Sleep 500ms
Up
Sleep 900ms

# ── Scene 3: live filter ──────────────────────────────────────────────────
Type "/"
Sleep 700ms
Type "abandoned"
Sleep 2.5s
Escape
Sleep 1s

# ── Scene 4: multi-select + bulk delete ───────────────────────────────────
Type "t"
Sleep 900ms
Space
Sleep 400ms
Down
Sleep 300ms
Space
Sleep 400ms
Down
Sleep 300ms
Space
Sleep 1.2s
Ctrl+D
Sleep 2.5s

# ── Scene 5: quit and show reclaimed space ────────────────────────────────
Ctrl+Q
Sleep 800ms
Type "killpy stats --path demo_projects"
Sleep 1s
Enter
Sleep 4s
Sleep 2s
