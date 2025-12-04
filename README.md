# Meeting Notes Processor for Capacities

Automatically processes meeting transcripts with AI and sends structured notes to Capacities.

## Features

- **AI-powered summarization** using local Ollama LLM
- **Structured output** with decisions, action items, timeline, etc.
- **Multiple input formats**: Meetily JSON, audio/video files, plain text
- **Whisper transcription**: Transcribe audio/video files locally
- **Context support**: Add participant names, meeting topics to improve AI accuracy
- **Raycast integration**: GUI with context dialog for easy processing

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

### Scan Mode (default)
Scans both the Meetily recordings folder and import folder for new files to process:

```bash
python meetily_capacities_sync.py
```

This will:
1. Check `$TRANSCRIPT_DIR` for Meetily recording folders with completed transcripts
2. Check `ALTER_TRANSCRIPT_DIR` (or the default `~/Library/Application Support/Alter/Transcripts` if not set) for Alter text/markdown/JSON transcripts
3. Check `$TRANSCRIPT_DIR/imported/` for audio/video files to transcribe

### Single File Mode
Process a specific file:

```bash
python meetily_capacities_sync.py /path/to/transcript.txt
python meetily_capacities_sync.py /path/to/meeting.mp4
python meetily_capacities_sync.py /path/to/meetily-folder/
```

### Adding Context
Provide additional context to help the AI (participant names, meeting topic, etc.):

```bash
python meetily_capacities_sync.py --context "Participants: John (PM), Sarah (Dev). Project: Alpha release planning"
python meetily_capacities_sync.py /path/to/file.mp4 --context "Weekly standup with engineering team"
```

### Raycast Integration

1. Open Raycast → Settings → Extensions → Script Commands
2. Add this repository's folder as a script directory
3. Search for "Process Meeting Notes" in Raycast

The Raycast command:
- Shows a **context dialog** first where you can enter participant names, meeting topic, etc.
- Displays real-time status updates
- Lets you cancel the process at any time
- Shows completion status when done

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
| `ALTER_TRANSCRIPT_DIR` | `~/Library/Application Support/Alter/Transcripts` | Alter transcripts directory for `.txt`/`.md`/`.json` transcripts (set in `.env`) |
| `LLM_MODEL` | `qwen3:8b` | Ollama model to use |
| `WHISPER_MODEL` | `base` | Whisper model for audio (see table below) |

### Whisper Model Sizes

Choose based on your speed vs accuracy needs:

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| `tiny` | 39 MB | ~32x realtime | Basic | Quick tests, clear audio |
| `base` | 74 MB | ~16x realtime | Good | Default, balanced |
| `small` | 244 MB | ~6x realtime | Better | Most meetings |
| `medium` | 769 MB | ~2x realtime | Great | Important recordings |
| `large` | 1.5 GB | ~1x realtime | Best | Critical accuracy needed |

> **Tip:** A 10-minute recording with `base` takes ~40 seconds. With `medium` it takes ~5 minutes.

### Ollama Model Options

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| `qwen3:4b` | ~2.5 GB | Fast | Good for simple meetings |
| `qwen3:8b` | ~5 GB | Medium | Default, balanced |
| `qwen3:14b` | ~9 GB | Slower | Better summaries |
| `llama3.2:3b` | ~2 GB | Fast | Lightweight alternative |
| `mistral:7b` | ~4 GB | Medium | Good general purpose |

To use a different model:
```bash
ollama pull <model-name>
# Then set LLM_MODEL=<model-name> in .env
```

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
