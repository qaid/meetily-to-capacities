# Meeting Notes Processor for Capacities

Automatically processes meeting transcripts with AI and sends structured notes to Capacities.

## Features

- **AI-powered summarization** using local Ollama LLM
- **Structured output** with decisions, action items, timeline, etc.
- **Multiple input formats**: Meetily JSON, audio/video files, plain text
- **Whisper transcription**: Transcribe audio/video files locally
- **Auto-watch mode**: Monitors directory for new transcripts
- **Single file mode**: Process individual files on demand

## Prerequisites

1. **Ollama** - Install from [ollama.ai](https://ollama.ai)
2. **Python 3.10-3.13** (3.14 not yet supported by Whisper)
3. **ffmpeg** - Required for audio/video processing (`brew install ffmpeg`)
4. **Capacities API token** - Get from Capacities → Settings → Capacities API

## Quick Install

```bash
# Clone or download this repository, then:
cd meetily-to-capacities
./install.sh
```

The install script will:
- Check for Python and Ollama
- Download the qwen3:8b model if needed
- Create a Python virtual environment
- Install all dependencies
- Create the import folder for audio/video files

Then edit `.env` with your Capacities credentials.

## Manual Setup

```bash
# 1. Install Ollama and pull the model
ollama pull qwen3:8b

# 2. Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Copy and edit .env
cp .env.example .env
# Edit .env with your Capacities token and space ID
```

## Usage

### Watch Mode (default)
Monitors the transcript directory for new files:

```bash
python meetily_capacities_sync.py
```

### Single File Mode
Process a specific file:

```bash
python meetily_capacities_sync.py /path/to/transcript.txt
python meetily_capacities_sync.py /path/to/meeting.mp4
python meetily_capacities_sync.py /path/to/meetily-folder/
```

### Scan Import Folder
Process all audio/video files in the import folder:

```bash
python meetily_capacities_sync.py --scan-imports
```

Drop files into `$TRANSCRIPT_DIR/imported/` and run this command.

### Raycast Integration

1. Open Raycast → Settings → Extensions → Script Commands
2. Add this repository's folder as a script directory
3. Search for "Process Meeting Notes" in Raycast

The Raycast command shows a progress window where you can:
- See real-time status updates
- Cancel the process at any time
- Close when complete

## Supported Input Formats

| Source | Format | Notes |
|--------|--------|-------|
| Meetily | Folder with `transcripts.json` + `metadata.json` | Auto-detects completed meetings |
| Audio/Video | `.mp3`, `.mp4`, `.wav`, `.m4a`, `.mov`, `.webm`, `.avi`, `.mkv`, `.flac`, `.ogg` | Transcribed with Whisper |
| Alter | `.txt` files | Plain transcript text |
| Generic | `.txt`, `.md`, `.json` | JSON must have `text`, `transcript`, or `segments` field |

> **Meetily Note:** You must enable "Save audio recordings" in Meetily settings for transcripts to be generated. Without this, only `metadata.json` is created.

## Output Structure

The AI generates structured notes with:

- **Meeting Metadata** - Date, duration, participants
- **Executive Summary** - 2-3 sentence overview
- **Decisions** - What was decided and by whom
- **Action Items** - Tasks with assignees and deadlines
- **Key Topics** - Discussion organized by theme
- **Timeline** - Deadlines and next meeting
- **Reference Info** - Facts, resources, follow-ups

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CAPACITIES_TOKEN` | - | Your Capacities API token |
| `CAPACITIES_SPACE_ID` | - | Target Capacities space ID |
| `TRANSCRIPT_DIR` | - | Meetily recordings directory (check Meetily settings for location) |
| `LLM_MODEL` | `qwen3:8b` | Ollama model to use |
| `WHISPER_MODEL` | `base` | Whisper model for audio (tiny/base/small/medium/large) |

## Troubleshooting

**"Ollama connection refused"**
- Make sure Ollama is running: `ollama serve`

**"Model not found"**
- Pull the model: `ollama pull qwen3:8b`

**"API Error 401"**
- Check your Capacities token is valid

**Processing is slow**
- First run downloads the model (~5GB for qwen3:8b)
- Subsequent runs are faster
- Consider a smaller model like `qwen3:4b` for speed
