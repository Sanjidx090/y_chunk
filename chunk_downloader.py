#!/usr/bin/env python3
"""
CHUNK-WISE BANGLA TRANSCRIPT DOWNLOADER
Downloads transcripts in time-based chunks for VAD alignment or processing
"""

# !pip -q install youtube-transcript-api pandas
import pandas as pd
import time
import random
import os
import json
from youtube_transcript_api import YouTubeTranscriptApi
import youtube_transcript_api._errors as yt_errors

# ==============================
# CONFIG - EDIT THESE
# ==============================
INPUT_CSV = "videos_with_bangla.csv"  # CSV with video IDs (from your availability check)
OUTPUT_DIR = "bangla_transcripts"  # Where to save transcripts
VIDEO_ID_COLUMN = "video_id"

# Chunking mode
CHUNK_MODE = "full"  # Options: "full", "fixed", "sentences", "custom"
# - "full": Download entire transcript as one piece
# - "fixed": Split into fixed-duration chunks (e.g., 30 seconds)
# - "sentences": Keep each sentence as separate chunk
# - "custom": Use time ranges from VAD output

# For "fixed" mode
CHUNK_DURATION = 30  # seconds per chunk

# For "custom" mode (provide your own time ranges)
# Format: {"video_id": [(start1, end1), (start2, end2), ...]}
CUSTOM_CHUNKS = {}

# Batch processing
START_INDEX = 0
BATCH_SIZE = 50  # Process this many videos

# Safety
MIN_WAIT = 2.0
MAX_WAIT = 4.0
SAVE_EVERY = 5  # Save progress every N videos

# Resume from previous run
RESUME = True

# ==============================
# SETUP
# ==============================
os.makedirs(OUTPUT_DIR, exist_ok=True)
progress_file = os.path.join(OUTPUT_DIR, "download_progress.json")

print("=" * 70)
print("CHUNK-WISE BANGLA TRANSCRIPT DOWNLOADER")
print("=" * 70)
print(f"Mode: {CHUNK_MODE}")
print(f"Output: {OUTPUT_DIR}/")
print()

# ==============================
# LOAD VIDEO LIST
# ==============================
df = pd.read_csv(INPUT_CSV)
all_video_ids = df[VIDEO_ID_COLUMN].dropna().astype(str).unique().tolist()
print(f"📌 Total Bangla videos: {len(all_video_ids)}")

# Check progress
downloaded = set()
if RESUME and os.path.exists(progress_file):
    with open(progress_file, 'r') as f:
        progress = json.load(f)
        downloaded = set(progress.get('completed', []))
    print(f"✅ Already downloaded: {len(downloaded)} videos")

# Filter and batch
remaining_videos = [vid for vid in all_video_ids if vid not in downloaded]
batch_videos = remaining_videos[START_INDEX:START_INDEX + BATCH_SIZE]

if len(batch_videos) == 0:
    print("\n✅ All videos already downloaded!")
    exit(0)

print(f"📝 Will download: {len(batch_videos)} videos in this batch")
print()

# ==============================
# API INSTANCE
# ==============================
api = YouTubeTranscriptApi()

# ==============================
# CHUNKING FUNCTIONS
# ==============================

def chunk_full(segments):
    """Return entire transcript as one chunk"""
    text = " ".join([seg.text for seg in segments])
    return [{
        'chunk_id': 0,
        'start': segments[0].start if segments else 0,
        'end': segments[-1].start + segments[-1].duration if segments else 0,
        'text': text,
        'segments': len(segments)
    }]

def chunk_fixed(segments, duration=30):
    """Split into fixed-duration chunks"""
    if not segments:
        return []
    
    chunks = []
    chunk_id = 0
    current_start = segments[0].start
    current_text = []
    current_segs = []
    
    for seg in segments:
        seg_end = seg.start + seg.duration
        
        # If this segment would exceed chunk duration, save current chunk
        if seg.start >= current_start + duration:
            if current_text:
                chunks.append({
                    'chunk_id': chunk_id,
                    'start': current_start,
                    'end': current_segs[-1].start + current_segs[-1].duration,
                    'text': " ".join(current_text),
                    'segments': len(current_segs)
                })
                chunk_id += 1
            current_start = seg.start
            current_text = []
            current_segs = []
        
        current_text.append(seg.text)
        current_segs.append(seg)
    
    # Save last chunk
    if current_text:
        chunks.append({
            'chunk_id': chunk_id,
            'start': current_start,
            'end': current_segs[-1].start + current_segs[-1].duration,
            'text': " ".join(current_text),
            'segments': len(current_segs)
        })
    
    return chunks

def chunk_sentences(segments):
    """Keep each segment as separate chunk (sentence-level)"""
    chunks = []
    for i, seg in enumerate(segments):
        chunks.append({
            'chunk_id': i,
            'start': seg.start,
            'end': seg.start + seg.duration,
            'text': seg.text,
            'segments': 1
        })
    return chunks

def chunk_custom(segments, time_ranges):
    """Use custom time ranges (e.g., from VAD output)"""
    chunks = []
    
    for chunk_id, (start_time, end_time) in enumerate(time_ranges):
        matching_segs = []
        for seg in segments:
            seg_end = seg.start + seg.duration
            # Check if segment overlaps with time range
            if seg.start < end_time and seg_end > start_time:
                matching_segs.append(seg)
        
        if matching_segs:
            text = " ".join([seg.text for seg in matching_segs])
            chunks.append({
                'chunk_id': chunk_id,
                'start': start_time,
                'end': end_time,
                'text': text,
                'segments': len(matching_segs)
            })
    
    return chunks

# ==============================
# DOWNLOAD FUNCTION
# ==============================

def download_transcript_chunks(video_id):
    """Download and chunk transcript for a video"""
    try:
        # Fetch Bangla transcript
        transcript = api.fetch(video_id, languages=['bn'])
        segments = list(transcript)
        
        if not segments:
            return {
                'success': False,
                'error': 'No segments found',
                'chunks': []
            }
        
        # Apply chunking based on mode
        if CHUNK_MODE == "full":
            chunks = chunk_full(segments)
        elif CHUNK_MODE == "fixed":
            chunks = chunk_fixed(segments, CHUNK_DURATION)
        elif CHUNK_MODE == "sentences":
            chunks = chunk_sentences(segments)
        elif CHUNK_MODE == "custom":
            time_ranges = CUSTOM_CHUNKS.get(video_id, [])
            if not time_ranges:
                # Fallback to full if no custom ranges provided
                chunks = chunk_full(segments)
            else:
                chunks = chunk_custom(segments, time_ranges)
        else:
            chunks = chunk_full(segments)
        
        # Save chunks to files
        video_dir = os.path.join(OUTPUT_DIR, video_id)
        os.makedirs(video_dir, exist_ok=True)
        
        # Save metadata
        metadata = {
            'video_id': video_id,
            'url': f'https://www.youtube.com/watch?v={video_id}',
            'total_chunks': len(chunks),
            'chunk_mode': CHUNK_MODE,
            'total_duration': segments[-1].start + segments[-1].duration,
            'total_segments': len(segments)
        }
        
        with open(os.path.join(video_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # Save each chunk
        for chunk in chunks:
            chunk_file = os.path.join(video_dir, f'chunk_{chunk["chunk_id"]:04d}.json')
            with open(chunk_file, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)
            
            # Also save as plain text
            txt_file = os.path.join(video_dir, f'chunk_{chunk["chunk_id"]:04d}.txt')
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(chunk['text'])
        
        return {
            'success': True,
            'chunks': len(chunks),
            'duration': metadata['total_duration']
        }
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many Requests" in error_msg:
            return {
                'success': False,
                'error': 'RateLimited',
                'chunks': 0
            }
        return {
            'success': False,
            'error': error_msg[:100],
            'chunks': 0
        }

# ==============================
# MAIN LOOP
# ==============================

print("🚀 Starting downloads...")
print("=" * 70)
print()

processed = 0
rate_limited = False
results = []

for i, video_id in enumerate(batch_videos):
    current_index = START_INDEX + i
    total_done = len(downloaded) + processed + 1
    
    print(f"📥 [{total_done}/{len(all_video_ids)}] Downloading: {video_id}")
    
    result = download_transcript_chunks(video_id)
    
    if result['success']:
        print(f"   ✅ Success: {result['chunks']} chunks, {result['duration']:.1f}s total")
        downloaded.add(video_id)
    else:
        if result['error'] == 'RateLimited':
            print(f"   🛑 Rate limited - stopping")
            rate_limited = True
            break
        else:
            print(f"   ❌ Error: {result['error']}")
    
    results.append({
        'video_id': video_id,
        'success': result['success'],
        'chunks': result.get('chunks', 0),
        'error': result.get('error', '')
    })
    
    processed += 1
    
    # Save progress
    if processed % SAVE_EVERY == 0:
        with open(progress_file, 'w') as f:
            json.dump({
                'completed': list(downloaded),
                'total': len(all_video_ids),
                'timestamp': time.time()
            }, f)
        print(f"   💾 Progress saved ({total_done} total)")
    
    # Delay
    if i < len(batch_videos) - 1:
        wait_time = random.uniform(MIN_WAIT, MAX_WAIT)
        time.sleep(wait_time)

# Final progress save
with open(progress_file, 'w') as f:
    json.dump({
        'completed': list(downloaded),
        'total': len(all_video_ids),
        'timestamp': time.time()
    }, f)

# ==============================
# SUMMARY
# ==============================

print("\n" + "=" * 70)
print("✅ BATCH COMPLETE")
print("=" * 70)
print()

success_count = sum(1 for r in results if r['success'])
total_chunks = sum(r['chunks'] for r in results)

print(f"📊 This batch: {processed} videos")
print(f"✅ Successful: {success_count}/{processed}")
print(f"📝 Total chunks: {total_chunks}")
print(f"💾 Saved to: {OUTPUT_DIR}/")
print()

print(f"📈 Overall progress: {len(downloaded)}/{len(all_video_ids)} videos")

if rate_limited:
    print()
    print("⚠️  RATE LIMITED - Wait 1-2 hours and re-run with RESUME=True")

print("=" * 70)
