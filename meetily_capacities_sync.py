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

import argparse

import ollama
import requests
from dotenv import load_dotenv

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
    
    def process_with_ai(self, transcript, context="", content_type="meeting"):
        """Generate structured notes using local LLM"""
        
        context_section = ""
        if context:
            context_section = f"""
CONTEXT PROVIDED BY USER:
{context}

Use this context to help understand the content and provide more accurate summaries.

"""
        
        if content_type == "meeting":
            prompt = self._get_meeting_prompt(transcript, context_section)
        else:
            prompt = self._get_summary_prompt(transcript, context_section)
        
        print(f"  🤖 Processing as {content_type} with {self.llm_model}...")
        
        response = ollama.chat(
            model=self.llm_model,
            messages=[{'role': 'user', 'content': prompt}]
        )
        
        return response['message']['content']
    
    def _get_meeting_prompt(self, transcript, context_section):
        """Prompt for meeting recordings"""
        return f"""Create a structured meeting summary optimized for a knowledge management system:
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

    def _get_summary_prompt(self, transcript, context_section):
        """Prompt for documentaries, video essays, TED talks, and educational presentations"""
        return f"""Create a comprehensive summary of this video content (documentary, video essay, TED talk, or presentation) optimized for a knowledge management system:
{context_section}
TRANSCRIPT:
{transcript}

OUTPUT FORMAT:

# Overview
- **Title/Topic**: [Infer the main subject]
- **Format**: [Documentary, video essay, TED talk, lecture, presentation, etc.]
- **Speaker/Creator**: [Name if identifiable]
- **Core Question**: [What central question or problem does this content address?]

# The Big Idea
A single paragraph capturing the central thesis, argument, or message. What is the speaker/creator trying to convince us of or help us understand?

# Key Arguments & Ideas
Present the main arguments or ideas in the order they build upon each other:

1. **[First major point]**
   - Supporting evidence or reasoning
   - Why this matters

2. **[Second major point]**
   - Supporting evidence or reasoning
   - Why this matters

(Continue for all major points)

# Narrative Arc
How does the content unfold? Summarize the structure:
- **Opening hook**: How does it grab attention?
- **Problem/Context**: What situation or challenge is presented?
- **Journey/Exploration**: How does the argument develop?
- **Resolution/Call to action**: What conclusion or action is proposed?

# Evidence & Examples
Key evidence, stories, case studies, or examples used to support the arguments:
- **Example 1**: Description and what it demonstrates
- **Example 2**: Description and what it demonstrates

# Memorable Moments

## Powerful Quotes
Direct quotes worth remembering (with context):
- "[Quote]" — regarding [topic]

## Striking Facts or Statistics
Surprising or impactful data points mentioned:
- [Fact/statistic and its significance]

## Stories or Anecdotes
Compelling narratives used to illustrate points.

# Implications & Takeaways

## Why This Matters
What are the broader implications of these ideas? Why should we care?

## Challenges to Conventional Thinking
Does this content challenge common assumptions? How?

## What To Do With This
Practical applications or changes in perspective this content suggests.

# Connections & Context

## Related Ideas
How does this connect to other concepts, movements, or thinkers?

## Further Exploration
Topics, people, or resources to explore for deeper understanding.

## Questions Raised
Interesting questions this content raises but doesn't fully answer.

---

FORMATTING REQUIREMENTS:
- Use markdown headers and lists
- Capture the persuasive structure and emotional arc, not just facts
- Use **bold** for key terms and central ideas
- Include direct quotes when they're particularly powerful
- Write "Not addressed" for sections with no relevant content

STYLE GUIDELINES:
- Preserve the speaker's voice and passion where possible
- Focus on the "why" as much as the "what"
- Capture what makes this content compelling, not just informative
- Help the reader understand both the content AND why it matters

Generate the structured summary now:"""
    
    def send_to_capacities(self, notes, source_name):
        """Send structured notes to Capacities via API"""
        
        headers = {
            "Authorization": f"Bearer {self.capacities_token}",
            "Content-Type": "application/json"
        }
        
        formatted_notes = notes
        
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
    
    def process_transcript(self, file_path, context="", content_type="meeting"):
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
            notes = self.process_with_ai(transcript, context, content_type)
            
            # Send to Capacities
            print("  📤 Sending to Capacities...")
            if self.send_to_capacities(notes, source_name):
                print("  ✅ Successfully sent to Capacities!")
                return True
            
            return False
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            return False


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
    parser = argparse.ArgumentParser(description="Process meeting transcripts")
    parser.add_argument("file", nargs="?", help="Single file or folder to process")
    parser.add_argument("--context", type=str, default="", help="Additional context for AI (e.g., participant names)")
    parser.add_argument("--type", type=str, choices=["meeting", "summary"], default="meeting",
                        help="Content type: 'meeting' for meeting notes, 'summary' for general video/audio summaries")
    args = parser.parse_args()
    
    context = args.context
    content_type = args.type
    
    # Single file mode
    if args.file:
        file_path = args.file
        print(f"📄 Processing single file: {file_path}")
        print(f"📋 Content type: {content_type}")
        
        if processor.process_transcript(file_path, context, content_type):
            processed_files.add(file_path)
            save_sync_state(processed_files)
            print("\n✨ Done!")
        else:
            sys.exit(1)
        return
    
    # Default: Scan both directories for unprocessed files
    print("=" * 60)
    print("🚀 Meeting Notes Processor")
    print("=" * 60)
    print(f"🤖 LLM Model: {LLM_MODEL}")
    print(f"📋 Content type: {content_type}")
    print(f"📍 Capacities Space: {CAPACITIES_SPACE_ID[:8]}...")
    print(f"📊 Previously processed: {len(processed_files)} files")
    print("=" * 60)
    
    total_found = 0
    
    # Scan Meetily recordings directory for folders with transcripts
    print(f"\n🔍 Scanning Meetily recordings: {TRANSCRIPT_DIR}")
    for item in TRANSCRIPT_DIR.iterdir():
        if item.is_dir():
            transcripts_file = item / "transcripts.json"
            metadata_file = item / "metadata.json"
            
            if transcripts_file.exists() and metadata_file.exists():
                # Check if meeting is completed
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    if metadata.get('status') != 'completed':
                        continue
                except:
                    continue
                
                if str(item) not in processed_files:
                    total_found += 1
                    if processor.process_transcript(item, context, content_type):
                        processed_files.add(str(item))
                        save_sync_state(processed_files)
    
    # Scan import directory for audio/video files
    if IMPORT_DIR.exists():
        print(f"\n🔍 Scanning import folder: {IMPORT_DIR}")
        for file_path in IMPORT_DIR.iterdir():
            if file_path.suffix.lower() in AUDIO_VIDEO_EXTENSIONS:
                if str(file_path) not in processed_files:
                    total_found += 1
                    if processor.process_transcript(file_path, context, content_type):
                        processed_files.add(str(file_path))
                        save_sync_state(processed_files)
    
    print("\n" + "=" * 60)
    if total_found == 0:
        print("✅ No new files to process")
    else:
        print(f"✨ Processed {total_found} file(s)!")
    print("=" * 60)


if __name__ == "__main__":
    main()