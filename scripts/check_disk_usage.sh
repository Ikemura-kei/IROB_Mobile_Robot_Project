#!/usr/bin/env bash

tmux kill-session -t quota-watch 2>/dev/null || true

gnome-terminal -- bash -c '
tmux new-session -d -s quota-watch \
  "watch -n 2.0 \"du -h --max-depth=1 ~ | sort -hr\""

tmux split-window -v -t quota-watch \
  "watch -n 1 \"fs quota\""

tmux attach-session -t quota-watch
' &
