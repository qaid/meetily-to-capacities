#!/bin/bash
# Meeting Notes Processor - Installation Script

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================="
echo "Meeting Notes Processor - Setup"
echo "=================================="
echo

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Install from https://brew.sh"
    exit 1
fi
echo "✓ Homebrew found"

# Check for Python 3.10-3.13 (3.14 not supported by Whisper)
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install with: brew install python@3.13"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MINOR" -gt 13 ]; then
    echo "⚠️  Python $PYTHON_VERSION detected. Whisper requires Python 3.10-3.13"
    echo "   Install with: brew install python@3.13"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION found"

# Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama not found. Install from https://ollama.ai"
    exit 1
fi
echo "✓ Ollama found"

# Check for ffmpeg (needed for Whisper audio processing)
if ! command -v ffmpeg &> /dev/null; then
    echo "⏳ Installing ffmpeg (required for audio processing)..."
    brew install ffmpeg
fi
echo "✓ ffmpeg found"

# Check for required Ollama model
if ! ollama list 2>/dev/null | grep -q "qwen3:8b"; then
    echo "⏳ Downloading qwen3:8b model (this may take a few minutes)..."
    ollama pull qwen3:8b
fi
echo "✓ qwen3:8b model ready"

# Create virtual environment with correct Python version
echo
echo "⏳ Setting up Python environment..."
if [ -d ".venv" ]; then
    echo "   Removing existing virtual environment..."
    rm -rf .venv
fi
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "✓ Dependencies installed (including Whisper for audio transcription)"

# Create directories
mkdir -p ~/Movies/meetily-recordings/imported
echo "✓ Created import folder: ~/Movies/meetily-recordings/imported"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo
    echo "⚠️  Created .env file - you need to add your Capacities credentials!"
    echo "   Edit .env and set:"
    echo "   - CAPACITIES_TOKEN (from Capacities → Settings → Capacities API)"
    echo "   - CAPACITIES_SPACE_ID (from Capacities → Settings → Space settings)"
else
    echo "✓ .env file exists"
fi

echo
echo "=================================="
echo "✅ Installation complete!"
echo "=================================="
echo
echo "Next steps:"
echo "  1. Edit .env with your Capacities credentials"
echo "  2. Activate the environment: source .venv/bin/activate"
echo "  3. Run the processor"
echo
echo "Usage:"
echo "  Watch mode:    python meetily_capacities_sync.py"
echo "  Single file:   python meetily_capacities_sync.py /path/to/file.mp4"
echo "  Scan imports:  python meetily_capacities_sync.py --scan-imports"
echo "  Raycast:       Add this folder to Raycast Script Commands"
echo
echo "Import folder for audio/video files:"
echo "  ~/Movies/meetily-recordings/imported/"
echo
