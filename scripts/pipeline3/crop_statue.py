#!/usr/bin/env python3
"""Crop each image to the statue/foreground region using DA3 depth.

Mask = depth in [d_min, d_max]; keep largest connected component; crop a box
around it (padded). Writes crops + a log of per-image crop geometry so camera
intrinsics can be re-derived. This removes sky/background that dominates SIFT
features and breaks pose estimation.
"""
import argparse, os, glob, numpy as np, cv2


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image_dir", required=True)
    p.add_argument("--depth_dir", required=True)
    p.add_argument("--out_dir", required=True)
    p.add_argument("--d_min", type=float, default=1.0)
    p.add_argument("--d_max", type=float, default=9.0)
    p.add_argument("--pad_frac", type=float, default=0.12, help="padding as fraction of bbox size")
    p.add_argument("--min_area_frac", type=float, default=0.005, help="min mask area as fraction of image")
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    img_paths = sorted(glob.glob(os.path.join(args.image_dir, "*.jpg")))
    log = []
    for f in img_paths:
        name = os.path.splitext(os.path.basename(f))[0]
        dpath = os.path.join(args.depth_dir, name + ".npy")
        img = cv2.imread(f)
        h, w = img.shape[:2]
        d = np.load(dpath)
        if d.shape != (h, w):
            d = cv2.resize(d, (w, h))
        mask = (d >= args.d_min) & (d <= args.d_max)
        if mask.mean() < args.min_area_frac:
            print(f"  {name}: mask too small ({mask.mean():.3f}), skip")
            continue
        # clean
        mask = mask.astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        if n < 2:
            print(f"  {name}: no component, skip")
            continue
        # largest component by area
        areas = stats[1:, cv2.CC_STAT_AREA]
        ci = 1 + int(np.argmax(areas))
        x, y, bw, bh = stats[ci][cv2.CC_STAT_LEFT], stats[ci][cv2.CC_STAT_TOP], \
                       stats[ci][cv2.CC_STAT_WIDTH], stats[ci][cv2.CC_STAT_HEIGHT]
        # padded box, clamped
        pad_x, pad_y = int(bw * args.pad_frac), int(bh * args.pad_frac)
        x0, y0 = max(0, x - pad_x), max(0, y - pad_y)
        x1, y1 = min(w, x + bw + pad_x), min(h, y + bh + pad_y)
        crop = img[y0:y1, x0:x1]
        if crop.size == 0:
            print(f"  {name}: empty crop, skip")
            continue
        out_path = os.path.join(args.out_dir, name + ".jpg")
        cv2.imwrite(out_path, crop)
        log.append((name, x0, y0, x1 - x0, y1 - y0))
        print(f"  {name}: bbox=({x},{y},{bw},{bh}) crop=({x0},{y0},{x1-x0}x{y1-y0}) "
              f"mask_frac={mask.mean():.3f}")

    with open(os.path.join(args.out_dir, "crop_geometry.txt"), "w") as fh:
        for name, x0, y0, cw, ch in log:
            fh.write(f"{name} {x0} {y0} {cw} {ch}\n")
    print(f"\n{len(log)} crops -> {args.out_dir}")


if __name__ == "__main__":
    main()
