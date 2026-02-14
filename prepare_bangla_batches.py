#!/usr/bin/env python3
"""
Prepare Bangla video batches for chunk-wise download
"""

import pandas as pd
import math

# ==============================
# CONFIG
# ==============================
INPUT_CSV = "videos_with_bangla.csv"  # From your availability check
VIDEO_ID_COLUMN = "video_id"
VIDEOS_PER_BATCH = 50

print("=" * 70)
print("BANGLA VIDEO BATCH SPLITTER")
print("=" * 70)
print()

# ==============================
# LOAD BANGLA VIDEOS
# ==============================
df = pd.read_csv(INPUT_CSV)

# Filter to only Bangla (should already be filtered, but just in case)
if 'has_bangla' in df.columns:
    df = df[df['has_bangla'] == True]

video_ids = df[VIDEO_ID_COLUMN].dropna().astype(str).unique().tolist()

print(f"📌 Total Bangla videos: {len(video_ids)}")
print(f"📦 Batch size: {VIDEOS_PER_BATCH} videos")

num_batches = math.ceil(len(video_ids) / VIDEOS_PER_BATCH)
print(f"📊 Will create: {num_batches} batches")
print()

# ==============================
# CREATE BATCHES
# ==============================

batch_info = []

for i in range(num_batches):
    start_idx = i * VIDEOS_PER_BATCH
    end_idx = min((i + 1) * VIDEOS_PER_BATCH, len(video_ids))
    
    batch_ids = video_ids[start_idx:end_idx]
    batch_df = pd.DataFrame({VIDEO_ID_COLUMN: batch_ids})
    
    filename = f"bangla_batch_{i}.csv"
    batch_df.to_csv(filename, index=False)
    
    print(f"✅ Created {filename}")
    print(f"   Videos {start_idx} to {end_idx-1} ({len(batch_ids)} videos)")
    
    batch_info.append({
        'Batch': i,
        'File': filename,
        'Start': start_idx,
        'End': end_idx - 1,
        'Count': len(batch_ids),
        'Platform': f'Platform {i+1}'
    })
    print()

# ==============================
# PLATFORM ASSIGNMENTS
# ==============================

platforms = [
    "Kaggle (Notebook 1)",
    "Google Colab (Account 1)",
    "GitHub Codespaces",
    "Google Colab (Account 2)",
    "Kaggle (Notebook 2)",
    "Any available platform"
]

for info in batch_info:
    idx = info['Batch']
    info['Platform'] = platforms[idx] if idx < len(platforms) else f"Platform {idx+1}"

assignment_df = pd.DataFrame(batch_info)
assignment_df.to_csv('bangla_batch_assignments.csv', index=False)

print("=" * 70)
print("PLATFORM ASSIGNMENTS")
print("=" * 70)
print(assignment_df.to_string(index=False))
print()
print("💾 Saved to: bangla_batch_assignments.csv")
print()

# ==============================
# DOWNLOAD CONFIG GENERATOR
# ==============================

print("=" * 70)
print("CONFIGURATION SNIPPETS")
print("=" * 70)
print()
print("Copy these into chunk_downloader.py for each platform:")
print()

for i in range(num_batches):
    print(f"# Platform {i+1} ({batch_info[i]['Platform']})")
    print(f'INPUT_CSV = "bangla_batch_{i}.csv"')
    print(f'OUTPUT_DIR = "batch_{i}_transcripts"')
    print(f'BATCH_SIZE = {batch_info[i]["Count"]}')
    print()

# ==============================
# NEXT STEPS
# ==============================

print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print()
print("1. Upload each bangla_batch_X.csv to its assigned platform")
print("2. Upload chunk_downloader.py to each platform")
print("3. Edit the CONFIG section in chunk_downloader.py:")
print("   - Set INPUT_CSV to the batch file")
print("   - Set OUTPUT_DIR to batch_X_transcripts")
print("   - Choose CHUNK_MODE (full/fixed/sentences/custom)")
print()
print("4. Run chunk_downloader.py on each platform")
print("5. Download the transcript folders")
print("6. Run merge_transcript_batches.py to combine everything")
print()
print("See CHUNK_STRATEGY.txt for detailed instructions!")
print("=" * 70)

# ==============================
# SUMMARY FILE
# ==============================

summary = {
    'total_videos': len(video_ids),
    'num_batches': num_batches,
    'videos_per_batch': VIDEOS_PER_BATCH,
    'batches': batch_info
}

import json
with open('bangla_download_plan.json', 'w') as f:
    json.dump(summary, f, indent=2)

print()
print("📄 Download plan saved to: bangla_download_plan.json")
