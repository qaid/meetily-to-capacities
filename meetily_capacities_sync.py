#!/usr/bin/env python3
"""
Meeting Notes Processor for Capacities
Reads transcript files (Meetily JSON or plain text), processes with AI, sends to Capacities
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import ollama
import requests
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Load .env file from script directory
load_dotenv(Path(__file__).parent / ".env")

# ============= CONFIGURATION =============
CAPACITIES_TOKEN = os.environ.get("CAPACITIES_TOKEN")
CAPACITIES_SPACE_ID = os.environ.get("CAPACITIES_SPACE_ID")

# Transcript source directory
# For Meetily: ~/Movies/meetily-recordings
# For Alter: ~/Library/Application Support/Alter/Transcripts
TRANSCRIPT_DIR = Path(os.path.expanduser(os.environ.get(
    "TRANSCRIPT_DIR", 
    "~/Movies/meetily-recordings"
)))

# Import directory for audio/video files to be transcribed with Whisper
IMPORT_DIR = Path(os.path.expanduser(os.environ.get(
    "IMPORT_DIR",
    "~/Movies/meetily-recordings/imported"
)))

# LLM model for processing (must be installed via: ollama pull qwen3:8b)
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3:8b")

# Whisper model for audio/video transcription (tiny, base, small, medium, large)
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")

# Supported audio/video extensions
AUDIO_VIDEO_EXTENSIONS = ('.mp3', '.mp4', '.wav', '.m4a', '.webm', '.mov', '.avi', '.mkv', '.flac', '.ogg')

# Track processed files
SYNC_STATE_FILE = Path.home() / ".meeting_notes_sync.json"


# ============= AI PROCESSING =============

class MeetingNotesProcessor:
    """Processes transcripts with AI and sends structured notes to Capacities"""
    
    def __init__(self, capacities_token, space_id, llm_model):
        self.capacities_token = capacities_token
        self.space_id = space_id
        self.llm_model = llm_model
        self.api_url = "https://api.capacities.io/save-to-daily-note"
    
    def read_transcript_file(self, file_path):
        """Read transcript from file (supports plain text, Meetily JSON, and audio/video)"""
        file_path = Path(file_path)
        
        # Handle Meetily folder structure
        if file_path.is_dir():
            return self._read_meetily_folder(file_path)
        
        # Handle audio/video files - transcribe with Whisper
        if file_path.suffix.lower() in AUDIO_VIDEO_EXTENSIONS:
            return self._transcribe_audio(file_path)
        
        # Handle plain text/markdown files
        if file_path.suffix in ('.txt', '.md'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Handle JSON files (could be Meetily transcripts.json or other)
        if file_path.suffix == '.json':
            return self._read_json_transcript(file_path)
        
        return None
    
    def _transcribe_audio(self, file_path):
        """Transcribe audio/video file using Whisper"""
        try:
            import whisper
        except ImportError:
            print("  ⚠️  Whisper not installed. Run: pip install openai-whisper")
            return None
        
        # Check if file has audio stream
        import subprocess
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', str(file_path)],
                capture_output=True, text=True
            )
            if not result.stdout.strip():
                print("  ⚠️  No audio stream found in file - cannot transcribe")
                return None
        except FileNotFoundError:
            print("  ⚠️  ffmpeg not installed. Run: brew install ffmpeg")
            return None
        
        print(f"  🎤 Transcribing with Whisper ({WHISPER_MODEL} model)...")
        print(f"     Loading model (this may take a moment on first run)...", flush=True)
        
        try:
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning)
            
            model = whisper.load_model(WHISPER_MODEL)
            print(f"     Model loaded. Transcribing audio...", flush=True)
            result = model.transcribe(str(file_path), fp16=False, verbose=False)
            return result['text']
        except Exception as e:
            print(f"  ⚠️  Transcription failed: {e}")
            return None
    
    def _read_meetily_folder(self, folder_path):
        """Read transcript from Meetily folder structure"""
        transcripts_file = folder_path / "transcripts.json"
        
        if not transcripts_file.exists():
            return None
        
        return self._read_json_transcript(transcripts_file)
    
    def _read_json_transcript(self, file_path):
        """Parse JSON transcript file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Meetily format: segments array
            if 'segments' in data:
                segments = data.get('segments', [])
                if segments:
                    return " ".join(
                        segment.get('text', '').strip()
                        for segment in segments
                    )
            
            # Generic format: look for text/transcript fields
            for key in ('text', 'transcript', 'content'):
                if key in data and isinstance(data[key], str):
                    return data[key]
            
            return None
        except (json.JSONDecodeError, KeyError):
            return None
    
    def process_with_ai(self, transcript, context=""):
        """Generate structured meeting notes using local LLM"""
        
        context_section = ""
        if context:
            context_section = f"""
CONTEXT PROVIDED BY USER:
{context}

Use this context to help identify participants, understand the meeting topic, and provide more accurate summaries.

"""
        
        prompt = f"""Create a structured meeting summary optimized for a knowledge management system:
{context_section}
TRANSCRIPT:
{transcript}

OUTPUT FORMAT:

# Meeting Metadata
- Date: [Extract or note if not mentioned]
- Duration: [Estimate from transcript]
- Participants: List all speakers with any identifying details

# Executive Summary
2-3 sentences capturing the meeting's core purpose and outcomes.

# Outcomes

## Decisions
List each decision made:
- **Decision**: Clear statement
- **Context**: Why this was decided
- **Owner**: Person responsible (if mentioned)

## Action Items
For each task identified:
- **Task**: Description
- **Assigned To**: Person responsible
- **Due Date**: Deadline or timeframe
- **Priority**: High/Medium/Low
- **Dependencies**: Any blockers or prerequisites

## Commitments & Agreements
Any promises, commitments, or agreements made between parties.

# Discussion

## Key Topics
Organize discussion by theme with main points under each topic.

## Questions Raised
Important questions that came up, noting if they were resolved.

## Concerns or Risks
Any issues, risks, or concerns highlighted.

# Timeline

## Deadlines
All dates mentioned in chronological order with associated deliverables.

## Next Meeting
Date, time, and agenda items if scheduled.

# Reference Information

## Important Facts or Data
Key numbers, statistics, or facts mentioned.

## External Resources
Documents, links, or resources referenced.

## Follow-up Required
Items requiring research, clarification, or future discussion.

---

FORMATTING REQUIREMENTS:
- Use markdown headers and lists
- Keep descriptions concise and scannable
- Use **bold** for critical items
- Include speaker attribution when relevant (e.g., "SPEAKER_01 proposed...")
- Write "Not discussed" for empty sections
- Maintain objective, factual tone

STYLE GUIDELINES:
- Be direct and specific
- Use simple, clear language
- Avoid repetition
- Focus on facts over interpretation
- When uncertain, note "unclear from transcript"

Generate the structured meeting notes now:"""

        print(f"  🤖 Processing with {self.llm_model}...")
        
        response = ollama.chat(
            model=self.llm_model,
            messages=[{'role': 'user', 'content': prompt}]
        )
        
        return response['message']['content']
    
    def send_to_capacities(self, notes, source_name):
        """Send structured notes to Capacities via API"""
        
        headers = {
            "Authorization": f"Bearer {self.capacities_token}",
            "Content-Type": "application/json"
        }
        
        formatted_notes = f"""# Meeting Notes
*Source: {source_name}*
*Processed: {datetime.now().strftime('%Y-%m-%d %H:%M')}*

---

{notes}

---
*Auto-processed from meeting transcript*
"""
        
        payload = {
            "spaceId": self.space_id,
            "mdText": formatted_notes
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return True
            else:
                print(f"  ❌ API Error {response.status_code}: {response.text}")
                return False
        
        except requests.RequestException as e:
            print(f"  ❌ Network error: {e}")
            return False
    
    def process_transcript(self, file_path, context=""):
        """Complete processing pipeline for a single transcript"""
        file_path = Path(file_path)
        source_name = file_path.name
        
        print(f"\n{'='*60}")
        print(f"Processing: {source_name}")
        print(f"{'='*60}")
        
        try:
            # Read transcript
            print("  📄 Reading transcript...")
            transcript = self.read_transcript_file(file_path)
            
            if not transcript or not transcript.strip():
                print("  ⚠️  Empty or unreadable transcript, skipping")
                return False
            
            # Process with AI
            notes = self.process_with_ai(transcript, context)
            
            # Send to Capacities
            print("  📤 Sending to Capacities...")
            if self.send_to_capacities(notes, source_name):
                print("  ✅ Successfully sent to Capacities!")
                return True
            
            return False
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            return False


# ============= FILE WATCHING =============

class TranscriptWatcher(FileSystemEventHandler):
    """Watches directory for new transcript files"""
    
    def __init__(self, processor, processed_files):
        self.processor = processor
        self.processed_files = processed_files
        self.file_extensions = ('.txt', '.md', '.json')
    
    def on_created(self, event):
        if event.is_directory:
            # Check if it's a Meetily-style folder with transcripts.json
            folder_path = Path(event.src_path)
            time.sleep(3)  # Wait for files to be written
            
            transcripts_file = folder_path / "transcripts.json"
            metadata_file = folder_path / "metadata.json"
            
            if transcripts_file.exists() and metadata_file.exists():
                # Check if meeting is completed
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    if metadata.get('status') != 'completed':
                        return
                except:
                    return
                
                if event.src_path not in self.processed_files:
                    if self.processor.process_transcript(event.src_path):
                        self.processed_files.add(event.src_path)
            return
        
        # Handle regular transcript files
        if event.src_path.endswith(self.file_extensions):
            if event.src_path not in self.processed_files:
                time.sleep(2)  # Wait for file to be fully written
                
                if self.processor.process_transcript(event.src_path):
                    self.processed_files.add(event.src_path)


# ============= SYNC STATE =============

def load_sync_state():
    """Load set of already-processed files"""
    if SYNC_STATE_FILE.exists():
        try:
            with open(SYNC_STATE_FILE, 'r') as f:
                return set(json.load(f))
        except:
            pass
    return set()


def save_sync_state(processed_files):
    """Save processed files to disk"""
    with open(SYNC_STATE_FILE, 'w') as f:
        json.dump(list(processed_files), f, indent=2)


# ============= MAIN =============

def main():
    print()
    
    # Validate configuration
    if not CAPACITIES_TOKEN:
        print("❌ Configuration Error")
        print("   Set CAPACITIES_TOKEN environment variable or edit the script")
        print("   (Get it from Capacities → Settings → Capacities API)")
        print()
        sys.exit(1)
    
    if not CAPACITIES_SPACE_ID:
        print("❌ Configuration Error")
        print("   Set CAPACITIES_SPACE_ID environment variable or edit the script")
        print("   (Get it from Capacities → Settings → Space settings)")
        print()
        sys.exit(1)
    
    if not TRANSCRIPT_DIR.exists():
        print(f"❌ Transcript directory not found: {TRANSCRIPT_DIR}")
        print("   Set TRANSCRIPT_DIR environment variable or edit the script")
        print()
        sys.exit(1)
    
    # Initialize processor
    processor = MeetingNotesProcessor(
        capacities_token=CAPACITIES_TOKEN,
        space_id=CAPACITIES_SPACE_ID,
        llm_model=LLM_MODEL
    )
    
    # Load sync state
    processed_files = load_sync_state()
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Process meeting transcripts")
    parser.add_argument("file", nargs="?", help="Single file or folder to process")
    parser.add_argument("--scan-imports", action="store_true", help="Scan import folder for audio/video files")
    parser.add_argument("--context", type=str, default="", help="Additional context for AI (e.g., participant names)")
    args = parser.parse_args()
    
    context = args.context
    
    # Scan import directory for unprocessed audio/video files
    if args.scan_imports:
        if not IMPORT_DIR.exists():
            print(f"❌ Import directory not found: {IMPORT_DIR}")
            sys.exit(1)
        
        print(f"🔍 Scanning {IMPORT_DIR} for audio/video files...\n")
        
        found = 0
        for file_path in IMPORT_DIR.iterdir():
            if file_path.suffix.lower() in AUDIO_VIDEO_EXTENSIONS:
                if str(file_path) not in processed_files:
                    found += 1
                    if processor.process_transcript(file_path, context):
                        processed_files.add(str(file_path))
                        save_sync_state(processed_files)
        
        if found == 0:
            print("No new audio/video files found.")
        else:
            print(f"\n✨ Processed {found} file(s)!")
        return
    
    # Single file mode
    if args.file:
        file_path = args.file
        print(f"📄 Processing single file: {file_path}")
        
        if processor.process_transcript(file_path, context):
            processed_files.add(file_path)
            save_sync_state(processed_files)
            print("\n✨ Done!")
        else:
            sys.exit(1)
        return
    
    # Watch mode
    print("=" * 60)
    print("🚀 Meeting Notes Processor")
    print("=" * 60)
    print(f"📂 Watching: {TRANSCRIPT_DIR}")
    print(f"🤖 LLM Model: {LLM_MODEL}")
    print(f"📍 Capacities Space: {CAPACITIES_SPACE_ID[:8]}...")
    print(f"💾 Sync state: {SYNC_STATE_FILE}")
    print(f"📊 Previously processed: {len(processed_files)} files")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)
    
    # Set up file watcher for Meetily transcripts
    observer = Observer()
    observer.schedule(
        TranscriptWatcher(processor, processed_files),
        str(TRANSCRIPT_DIR),
        recursive=True
    )
    
    # Also watch import directory for audio/video files
    if IMPORT_DIR.exists() and IMPORT_DIR != TRANSCRIPT_DIR:
        print(f"📂 Import folder: {IMPORT_DIR}")
        observer.schedule(
            TranscriptWatcher(processor, processed_files),
            str(IMPORT_DIR),
            recursive=False
        )
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        save_sync_state(processed_files)
        print("\n\n" + "=" * 60)
        print("👋 Stopped watching")
        print(f"📊 Total processed: {len(processed_files)} files")
        print("=" * 60)
    
    observer.join()


if __name__ == "__main__":
    main()