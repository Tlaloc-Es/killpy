# demo.tape — killpy GIF for README
# Requires: vhs (https://github.com/charmbracelet/vhs)
# Usage: vhs demo.tape
#
# Workflow:
#   1. ./tester.sh setup     <- creates fake environments in ./demo_projects/
#   2. vhs demo.tape         <- records the GIF
#   3. ./tester.sh cleanup   <- cleans up (optional)

Output show.gif

Set Shell "bash"
Set FontSize 13
Set Width 1280
Set Height 720
Set Theme "Dracula"
Set Padding 20
Set TypingSpeed 55ms
Set PlaybackSpeed 0.85

# --- Setup: silent, clean ---
Hide
Type "export HISTFILE=/dev/null && export PS1='$ ' && clear"
Enter
Sleep 300ms
Type "bash tester.sh setup"
Enter
Sleep 4s
Type "clear"
Enter
Sleep 300ms
Show

# -----------------------------------------------------------------------
# SCENE 1 — Launch the TUI
# -----------------------------------------------------------------------
Sleep 600ms
Type "killpy --path ./demo_projects"
Sleep 1s
Enter

# Let the TUI appear and the scan start
Sleep 5s

# -----------------------------------------------------------------------
# SCENE 2 — Explore the table: see HIGH / MED / LOW colors
# -----------------------------------------------------------------------
# Scroll slowly to showcase the color coding
Down
Sleep 350ms
Down
Sleep 350ms
Down
Sleep 350ms
Down
Sleep 350ms
Down
Sleep 500ms

# Go back up to position on a HIGH entry
Up
Sleep 250ms
Up
Sleep 250ms
Up
Sleep 250ms
Up
Sleep 400ms

# -----------------------------------------------------------------------
# SCENE 3 — Filter: search for abandoned environments
# -----------------------------------------------------------------------
Type "/"
Sleep 400ms
Type "abandoned"
Sleep 1.2s
# View filter results
Sleep 800ms
Escape
Sleep 600ms

# -----------------------------------------------------------------------
# SCENE 4 — Filter by "old" to find old projects
# -----------------------------------------------------------------------
Type "/"
Sleep 300ms
Type "old"
Sleep 1s
Sleep 600ms
Escape
Sleep 500ms

# -----------------------------------------------------------------------
# SCENE 5 — Multi-select and bulk delete
# -----------------------------------------------------------------------
# Enable multi-select mode
Type "t"
Sleep 500ms

# Select multiple rows
Space
Sleep 200ms
Down
Sleep 150ms
Space
Sleep 200ms
Down
Sleep 150ms
Space
Sleep 200ms
Down
Sleep 150ms
Space
Sleep 400ms

# Pause to show selected rows before deletion
Sleep 800ms

# Confirm deletion of selected items
Ctrl+D
Sleep 600ms
Enter
Sleep 1.5s

# -----------------------------------------------------------------------
# SCENE 6 — Show freed space (updated status label)
# -----------------------------------------------------------------------
Sleep 1s

# -----------------------------------------------------------------------
# SCENE 7 — Exit
# -----------------------------------------------------------------------
Ctrl+Q
Sleep 400ms

# -----------------------------------------------------------------------
# SCENE 8 — Final stats: the “wow” moment of freed GBs
# -----------------------------------------------------------------------
Sleep 400ms
Type "killpy stats --path ./demo_projects"
Sleep 800ms
Enter
Sleep 3.5s
