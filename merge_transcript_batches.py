#!/usr/bin/env python3
"""
Merge transcript batches from all platforms into organized structure
"""

import os
import json
import shutil
import pandas as pd
from pathlib import Path

print("=" * 70)
print("TRANSCRIPT BATCH MERGER")
print("=" * 70)
print()

# ==============================
# FIND BATCH DIRECTORIES
# ==============================

print("🔍 Looking for transcript batch directories...")
print()

# Look for directories named batch_X_transcripts
batch_dirs = []
for item in os.listdir('.'):
    if os.path.isdir(item) and 'batch' in item.lower() and 'transcript' in item.lower():
        batch_dirs.append(item)

batch_dirs.sort()

if not batch_dirs:
    print("❌ No batch directories found!")
    print()
    print("Expected directories like:")
    print("  - batch_0_transcripts/")
    print("  - batch_1_transcripts/")
    print("  - etc.")
    print()
    print("Make sure you've downloaded transcript folders from all platforms")
    print("and placed them in the current directory.")
    exit(1)

print(f"Found {len(batch_dirs)} batch directories:")
for bd in batch_dirs:
    video_count = len([d for d in os.listdir(bd) if os.path.isdir(os.path.join(bd, d))])
    print(f"  ✅ {bd} ({video_count} videos)")
print()

# ==============================
# MERGE INTO SINGLE DIRECTORY
# ==============================

output_dir = "bangla_transcripts_merged"
os.makedirs(output_dir, exist_ok=True)

print(f"📦 Merging all transcripts into: {output_dir}/")
print()

all_videos = []
total_chunks = 0
errors = []

for batch_dir in batch_dirs:
    print(f"Processing {batch_dir}...")
    
    # Get all video directories in this batch
    video_dirs = [d for d in os.listdir(batch_dir) 
                  if os.path.isdir(os.path.join(batch_dir, d))]
    
    for video_id in video_dirs:
        source_path = os.path.join(batch_dir, video_id)
        dest_path = os.path.join(output_dir, video_id)
        
        # Check if this video already exists (duplicate)
        if os.path.exists(dest_path):
            print(f"  ⚠️  Skipping duplicate: {video_id}")
            continue
        
        try:
            # Copy entire video directory
            shutil.copytree(source_path, dest_path)
            
            # Read metadata
            metadata_file = os.path.join(dest_path, 'metadata.json')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    all_videos.append({
                        'video_id': video_id,
                        'chunks': metadata.get('total_chunks', 0),
                        'duration': metadata.get('total_duration', 0),
                        'mode': metadata.get('chunk_mode', 'unknown'),
                        'url': metadata.get('url', '')
                    })
                    total_chunks += metadata.get('total_chunks', 0)
            
            print(f"  ✅ {video_id}")
            
        except Exception as e:
            print(f"  ❌ Error copying {video_id}: {e}")
            errors.append({'video_id': video_id, 'error': str(e)})
    
    print()

# ==============================
# CREATE SUMMARY
# ==============================

print("=" * 70)
print("CREATING SUMMARY FILES")
print("=" * 70)
print()

# Summary CSV
summary_df = pd.DataFrame(all_videos)
summary_csv = "transcript_download_summary.csv"
summary_df.to_csv(summary_csv, index=False)
print(f"📄 Summary CSV: {summary_csv}")

# Statistics
stats = {
    'total_videos': len(all_videos),
    'total_chunks': total_chunks,
    'avg_chunks_per_video': total_chunks / len(all_videos) if all_videos else 0,
    'total_duration_hours': sum(v['duration'] for v in all_videos) / 3600,
    'errors': len(errors)
}

# Save stats
with open('transcript_stats.json', 'w') as f:
    json.dump(stats, f, indent=2)
print(f"📊 Statistics: transcript_stats.json")

# Create index file (useful for quick lookup)
index = {video['video_id']: {
    'chunks': video['chunks'],
    'duration': video['duration'],
    'url': video['url']
} for video in all_videos}

with open(os.path.join(output_dir, 'index.json'), 'w') as f:
    json.dump(index, f, indent=2)
print(f"📇 Index: {output_dir}/index.json")

print()

# ==============================
# FINAL STATISTICS
# ==============================

print("=" * 70)
print("✅ MERGE COMPLETE")
print("=" * 70)
print()

print(f"📊 Total videos: {stats['total_videos']}")
print(f"📝 Total chunks: {stats['total_chunks']}")
print(f"📈 Avg chunks/video: {stats['avg_chunks_per_video']:.1f}")
print(f"⏱️  Total duration: {stats['total_duration_hours']:.1f} hours")

if errors:
    print(f"⚠️  Errors: {len(errors)}")
    print()
    print("Videos with errors:")
    for err in errors[:10]:  # Show first 10
        print(f"  - {err['video_id']}: {err['error']}")

print()
print(f"📁 All transcripts merged into: {output_dir}/")
print()

# Chunk mode breakdown
if all_videos:
    mode_counts = summary_df['mode'].value_counts()
    print("Chunk modes used:")
    for mode, count in mode_counts.items():
        print(f"  {mode}: {count} videos")

print()

# ==============================
# DIRECTORY STRUCTURE INFO
# ==============================

print("=" * 70)
print("DIRECTORY STRUCTURE")
print("=" * 70)
print()
print(f"{output_dir}/")
print("├── index.json              - Quick lookup index")
print("├── VIDEO_ID_1/")
print("│   ├── metadata.json")
print("│   ├── chunk_0000.json")
print("│   ├── chunk_0000.txt")
print("│   └── ...")
print("├── VIDEO_ID_2/")
print("└── ...")
print()

# ==============================
# USAGE EXAMPLES
# ==============================

print("=" * 70)
print("USAGE EXAMPLES")
print("=" * 70)
print()
print("1. Get transcript for specific video:")
print(f"   cat {output_dir}/VIDEO_ID/chunk_0000.txt")
print()
print("2. Count total chunks:")
print(f"   find {output_dir} -name 'chunk_*.json' | wc -l")
print()
print("3. Get all text for training:")
print(f"   cat {output_dir}/*/chunk_*.txt > all_bangla_text.txt")
print()
print("4. Load in Python:")
print("   import json")
print(f"   with open('{output_dir}/VIDEO_ID/chunk_0000.json') as f:")
print("       chunk = json.load(f)")
print()

print("=" * 70)
print("🎉 Done!")
print("=" * 70)
