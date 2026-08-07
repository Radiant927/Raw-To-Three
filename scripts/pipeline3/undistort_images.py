#!/usr/bin/env python3
"""Undistort images using COLMAP SIMPLE_RADIAL k1 params.

For each registered image:
1. Read camera params (f, cx, cy, k1) from COLMAP
2. Build K matrix, run cv2.undistort with alpha=1.0
3. Save undistorted image + matching undistorted mask
4. Output new_K (fx, fy, cx, cy) for camera patching

Output directory structure:
  <output_dir>/images_undistorted/   — undistorted PNGs
  <output_dir>/masks_undistorted/    — undistorted masks (if masks_dir provided)
  <output_dir>/cam_updates.json      — new camera intrinsics per cam_id
"""
import argparse, cv2, json, os, numpy as np
from PIL import Image
import pycolmap


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--colmap_dir", required=True, help="COLMAP dir with sparse/0/ and images/")
    p.add_argument("--masks_dir", default=None, help="Optional: original masks dir")
    p.add_argument("--output_dir", required=True, help="Output base directory")
    args = p.parse_args()

    sparse0 = os.path.join(args.colmap_dir, "sparse", "0")
    img_dir = os.path.join(args.colmap_dir, "images")

    recon = pycolmap.Reconstruction(sparse0)

    img_out = os.path.join(args.output_dir, "images_undistorted")
    mask_out = os.path.join(args.output_dir, "masks_undistorted")
    os.makedirs(img_out, exist_ok=True)
    if args.masks_dir:
        os.makedirs(mask_out, exist_ok=True)

    cam_updates = {}

    for img_id in sorted(recon.images.keys()):
        img = recon.images[img_id]
        cam = recon.cameras[img.camera_id]

        if cam.model.name != "SIMPLE_RADIAL":
            print(f"  [{img_id}] {cam.model.name} — skipping (already undistorted?)")
            continue

        f, cx, cy, k1 = cam.params
        K = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1]], dtype=np.float64)
        dist = np.array([k1, 0.0, 0.0, 0.0])

        img_path = os.path.join(img_dir, img.name)
        if not os.path.exists(img_path):
            for ext in ['.jpg', '.png', '.JPG', '.PNG', '.jpeg']:
                alt = os.path.join(img_dir, os.path.splitext(img.name)[0] + ext)
                if os.path.exists(alt):
                    img_path = alt
                    break

        image = cv2.imread(img_path)
        if image is None:
            print(f"  [{img_id}] WARNING: cannot read {img_path}, skipping")
            continue
        h, w = image.shape[:2]

        new_K, _ = cv2.getOptimalNewCameraMatrix(K, dist, (w, h), alpha=1.0)
        undistorted = cv2.undistort(image, K, dist, None, new_K)

        base = os.path.splitext(img.name)[0]
        out_path = os.path.join(img_out, base + ".png")
        cv2.imwrite(out_path, undistorted)

        # Undistort mask if available
        if args.masks_dir:
            mask_path = os.path.join(args.masks_dir, base + ".png")
            if os.path.exists(mask_path):
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                mask_und = cv2.undistort(mask, K, dist, None, new_K)
                cv2.imwrite(os.path.join(mask_out, base + ".png"), mask_und)

        cam_updates[str(img.camera_id)] = {
            "fx": float(new_K[0, 0]), "fy": float(new_K[1, 1]),
            "cx": float(new_K[0, 2]), "cy": float(new_K[1, 2]),
            "width": w, "height": h,
        }

    with open(os.path.join(args.output_dir, "cam_updates.json"), "w") as f:
        json.dump(cam_updates, f, indent=2)

    print(f"Done: {len(cam_updates)} cameras undistorted")
    print(f"  Images: {img_out}")
    if args.masks_dir:
        print(f"  Masks: {mask_out}")
    print(f"  Updates: {os.path.join(args.output_dir, 'cam_updates.json')}")


if __name__ == "__main__":
    main()
