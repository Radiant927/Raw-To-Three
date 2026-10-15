#!/usr/bin/env bash
# End-to-end COLMAP + Brush pipeline for image folder -> final PLY.
# Usage: run_pipeline.sh <images_dir> <output_dir> [iterations] [gpu_id]
#
# Steps:
#   1. feature_extractor (SIFT, GPU if available)
#   2. exhaustive_matcher
#   3. mapper (incremental SfM)
#   4. image_undistorter
#   5. brush-cli training
#   6. export final PLY
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COLMAP_BIN="$ROOT_DIR/colmap/bin/colmap"
BRUSH_BIN="$ROOT_DIR/brush/brush-cli"

IMAGES_DIR="${1:?images_dir required}"
OUTPUT_DIR="${2:?output_dir required}"
ITERATIONS="${3:-15000}"
GPU_ID="${4:-0}"

mkdir -p "$OUTPUT_DIR"
LOG_FILE="$OUTPUT_DIR/pipeline.log"

log() {
    echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

mark_step() {
    local step="$1" status="$2"
    echo "$step:$status" > "$OUTPUT_DIR/.step_$step"
}

export CUDA_VISIBLE_DEVICES="$GPU_ID"

log "Pipeline start. images=$IMAGES_DIR out=$OUTPUT_DIR iter=$ITERATIONS gpu=$GPU_ID"

# ---- 1. Feature extraction ----
log "[1/6] Feature extraction..."
mark_step colmap running
"$COLMAP_BIN" feature_extractor \
    --database_path "$OUTPUT_DIR/database.db" \
    --image_path "$IMAGES_DIR" \
    --SiftExtraction.use_gpu 1 \
    --SiftExtraction.max_image_size 2000 \
    --SiftExtraction.max_num_features 8192 \
    >>"$LOG_FILE" 2>&1
log "  feature extraction done"

# ---- 2. Matching ----
log "[2/6] Exhaustive matching..."
"$COLMAP_BIN" exhaustive_matcher \
    --database_path "$OUTPUT_DIR/database.db" \
    --SiftMatching.use_gpu 1 \
    --SiftMatching.guided_matching 1 \
    >>"$LOG_FILE" 2>&1
log "  matching done"

# ---- 3. Mapper ----
log "[3/6] Mapper (incremental SfM)..."
mkdir -p "$OUTPUT_DIR/sparse"
"$COLMAP_BIN" mapper \
    --database_path "$OUTPUT_DIR/database.db" \
    --image_path "$IMAGES_DIR" \
    --output_path "$OUTPUT_DIR/sparse" \
    --Mapper.ba_global_max_num_iterations 50 \
    --Mapper.ba_local_max_num_iterations 25 \
    --Mapper.init_min_num_inliers 100 \
    --Mapper.abs_pose_min_num_inliers 30 \
    >>"$LOG_FILE" 2>&1

# Find the largest reconstruction (usually 0)
SPARSE_DIR=""
for d in "$OUTPUT_DIR/sparse"/[0-9]*; do
    if [ -f "$d/cameras.bin" ] || [ -f "$d/cameras.txt" ]; then
        SPARSE_DIR="$d"
        break
    fi
done
if [ -z "$SPARSE_DIR" ]; then
    log "ERROR: no reconstruction produced"
    mark_step colmap failed
    exit 1
fi
log "  reconstruction: $(basename "$SPARSE_DIR")"

# ---- 4. Image undistorter ----
log "[4/6] Image undistortion..."
"$COLMAP_BIN" image_undistorter \
    --image_path "$IMAGES_DIR" \
    --input_path "$SPARSE_DIR" \
    --output_path "$OUTPUT_DIR/dense" \
    --output_type COLMAP \
    --max_image_size 1600 \
    >>"$LOG_FILE" 2>&1
log "  undistortion done"

DENSE_IMG="$OUTPUT_DIR/dense/images"
DENSE_SPARSE="$OUTPUT_DIR/dense/sparse"

# ---- 5. Brush training ----
log "[5/6] Brush training ($ITERATIONS iters)..."
mark_step train running

export RUST_LOG=info
"$BRUSH_BIN" "$DENSE_IMG" \
    --total-train-iters "$ITERATIONS" \
    --colmap-model "$DENSE_SPARSE" \
    --export-path "$OUTPUT_DIR/exports" \
    --export-name "final.ply" \
    --export-every "$ITERATIONS" \
    --max-resolution 1600 \
    --max-splats 2000000 \
    --background-color 1 1 1 \
    >>"$LOG_FILE" 2>&1
log "  training done"
mark_step train done

# ---- 6. Copy final PLY ----
log "[6/6] Collecting final output..."
FINAL_PLY=""
for f in "$OUTPUT_DIR/exports"/*/final.ply "$OUTPUT_DIR/exports/final.ply"; do
    if [ -f "$f" ]; then
        FINAL_PLY="$f"
        break
    fi
done
if [ -z "$FINAL_PLY" ]; then
    log "ERROR: final PLY not found"
    exit 1
fi
mkdir -p "$OUTPUT_DIR/result"
cp "$FINAL_PLY" "$OUTPUT_DIR/result/denoised_3dgs.ply"
log "  final PLY -> $OUTPUT_DIR/result/denoised_3dgs.ply"
log "Done."
mark_step export done
mark_step colmap done
