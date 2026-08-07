#!/usr/bin/env bash
# Pipeline V3: Undistort → DA3 Depth → 2DGS with Depth Loss → Export
#
# Usage:
#   bash run_pipeline3.sh <raw_photos_dir> <output_name> [options]
#
# Example:
#   bash run_pipeline3.sh ~/library_v3 library_p3
#
# Prerequisites:
#   - ~/da3_env/bin/python exists (DA3 + pycolmap + opencv)
#   - ~/2d-gs/ exists (2DGS training code)
#   - SCRIPT_DIR points to this script's directory with all .py files
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-$HOME/da3_env/bin/python}"
GS_DIR="${GS_DIR:-$HOME/2d-gs}"
COLMAP_SCRIPT="$SCRIPT_DIR/../run_colmap.py"
UNDISTORT="$SCRIPT_DIR/undistort_images.py"
PATCH_CAM="$SCRIPT_DIR/patch_cameras.py"
PRED_DEPTH="$SCRIPT_DIR/predict_depth.py"
PATCH_GS="$SCRIPT_DIR/patch_2dgs_for_depth.py"
DENOISE="$SCRIPT_DIR/denoise_post.py"
CONVERT_3DGS="$SCRIPT_DIR/../convert_to_3dgs.py"
EXPORT_GLB="$SCRIPT_DIR/../export_glb.py"

# Parse args
RAW_DIR="${1:?Usage: $0 <raw_photos_dir> <output_name>}"
NAME="${2:?Usage: $0 <raw_photos_dir> <output_name>}"
ITERS="${ITERS:-30000}"
GPU="${GPU:-0}"
SKIP_COLMAP="${SKIP_COLMAP:-0}"

WORK_DIR="$HOME/rt_pipeline_test/${NAME}"
echo "=== Pipeline V3 ==="
echo "  Raw photos: $RAW_DIR"
echo "  Work dir:   $WORK_DIR"
echo "  GPU:        $GPU"
echo "  Iters:      $ITERS"
echo ""

mkdir -p "$WORK_DIR"

# ── Step 1: COLMAP SfM (SIMPLE_RADIAL) ──
COLMAP_DIR="$WORK_DIR/colmap_out"
if [ "$SKIP_COLMAP" != "1" ]; then
    echo "=== Step 1: COLMAP SfM ==="
    # Create colmap directory structure
    mkdir -p "$COLMAP_DIR"
    if [ ! -d "$COLMAP_DIR/images" ]; then
        ln -sf "$(realpath "$RAW_DIR")" "$COLMAP_DIR/images"
    fi
    $PYTHON "$COLMAP_SCRIPT" --image_path "$COLMAP_DIR/images" --output_path "$COLMAP_DIR/sparse"
    echo ""
else
    echo "=== Step 1: SKIP (COLMAP already done at $COLMAP_DIR) ==="
    echo ""
fi

SPARSE0="$COLMAP_DIR/sparse/0"
if [ ! -f "$SPARSE0/cameras.bin" ]; then
    echo "ERROR: COLMAP output not found at $SPARSE0"
    exit 1
fi

# ── Step 2: Undistort images ──
echo "=== Step 2: Undistort images (OpenCV + COLMAP k1) ==="
UNDIST_DIR="$WORK_DIR/undistorted"
$PYTHON "$UNDISTORT" \
    --colmap_dir "$COLMAP_DIR" \
    --masks_dir "$COLMAP_DIR/masks" \
    --output_dir "$UNDIST_DIR"
echo ""

# ── Step 3: Create clean working directory with PINHOLE cameras ──
echo "=== Step 3: Build PINHOLE camera dataset ==="
DATA_DIR="$WORK_DIR/data"
rm -rf "$DATA_DIR"
mkdir -p "$DATA_DIR/sparse/0"

# Symlink undistorted images and masks
ln -sf "$UNDIST_DIR/images_undistorted" "$DATA_DIR/images"
if [ -d "$UNDIST_DIR/masks_undistorted" ]; then
    ln -sf "$UNDIST_DIR/masks_undistorted" "$DATA_DIR/masks"
fi

# Patch cameras.bin: SIMPLE_RADIAL → SIMPLE_PINHOLE
$PYTHON "$PATCH_CAM" \
    --input "$SPARSE0/cameras.bin" \
    --output "$DATA_DIR/sparse/0/cameras.bin" \
    --cam_updates "$UNDIST_DIR/cam_updates.json"

# Copy images.bin and points3D.bin unchanged
cp "$SPARSE0/images.bin" "$DATA_DIR/sparse/0/images.bin"
cp "$SPARSE0/points3D.bin" "$DATA_DIR/sparse/0/points3D.bin"

echo "Dataset ready at $DATA_DIR"
echo "  Images: $(ls $DATA_DIR/images | wc -l)"
echo "  Masks:  $([ -d $DATA_DIR/masks ] && ls $DATA_DIR/masks | wc -l || echo 'none')"
echo ""

# ── Step 4: DA3 depth prediction ──
echo "=== Step 4: DA3 metric depth prediction ==="
$PYTHON "$PRED_DEPTH" \
    --colmap_dir "$DATA_DIR" \
    --batch_size 2
echo ""

# ── Step 5: Patch 2DGS for depth loss ──
echo "=== Step 5: Patch 2DGS for depth loss support ==="
$PYTHON "$PATCH_GS" --gs_dir "$GS_DIR"
echo ""

# ── Step 6: Train 2DGS with depth loss ──
echo "=== Step 6: 2DGS training (color + depth loss) ==="
OUTPUT_DIR="$WORK_DIR/output"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

cd "$GS_DIR"
CUDA_VISIBLE_DEVICES="$GPU" $PYTHON train.py \
    -s "$DATA_DIR" \
    -m "$OUTPUT_DIR" \
    --use_depth_loss \
    --iterations "$ITERS" \
    --save_iterations "$ITERS" \
    --test_iterations "$((ITERS/2)) $ITERS" \
    --masks "masks"
echo ""

# ── Step 7: Denoise and export ──
echo "=== Step 7: Post-training filter + export ==="
TRAINED_PLY="$OUTPUT_DIR/point_cloud/iteration_${ITERS}/point_cloud.ply"
if [ ! -f "$TRAINED_PLY" ]; then
    echo "ERROR: Trained PLY not found at $TRAINED_PLY"
    exit 1
fi

DENOISED_PLY="$WORK_DIR/denoised.ply"
$PYTHON "$DENOISE" --input "$TRAINED_PLY" --output "$DENOISED_PLY" --opacity_min 0.09

# Convert to 3DGS format (adds scale_2)
PLY_3DGS="$WORK_DIR/denoised_3dgs.ply"
$PYTHON "$CONVERT_3DGS" --input "$DENOISED_PLY" --output "$PLY_3DGS"

# Export GLB
GLB_OUT="$WORK_DIR/${NAME}.glb"
$PYTHON "$EXPORT_GLB" --input "$DENOISED_PLY" --output "$GLB_OUT"

echo ""
echo "=== Pipeline V3 Complete ==="
echo "  Raw PLY:    $TRAINED_PLY"
echo "  Denoised:   $DENOISED_PLY"
echo "  3DGS PLY:   $PLY_3DGS"
echo "  GLB:        $GLB_OUT"
