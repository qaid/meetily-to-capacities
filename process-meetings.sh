#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Process Meeting Notes
# @raycast.mode silent
# @raycast.packageName Meeting Notes

# Optional parameters:
# @raycast.icon 🎙️

# Documentation:
# @raycast.description Process meeting transcripts and audio/video files with AI, send to Capacities
# @raycast.author Qaid
# @raycast.authorURL https://github.com/qaid

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Launch the GUI runner
swift "$SCRIPT_DIR/run_gui.swift" "$SCRIPT_DIR" "scan"
