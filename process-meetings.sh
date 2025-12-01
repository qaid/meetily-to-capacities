#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Process Meeting Notes
# @raycast.mode silent
# @raycast.packageName Meeting Notes

# Optional parameters:
# @raycast.icon 🎙️
# @raycast.argument1 { "type": "dropdown", "placeholder": "Action", "data": [{"title": "Scan Imports", "value": "scan"}, {"title": "Watch Mode", "value": "watch"}] }

# Documentation:
# @raycast.description Process meeting transcripts and audio/video files with AI, send to Capacities
# @raycast.author Qaid
# @raycast.authorURL https://github.com/qaid

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ACTION="${1:-scan}"

# Launch the GUI runner
swift "$SCRIPT_DIR/run_gui.swift" "$SCRIPT_DIR" "$ACTION"
