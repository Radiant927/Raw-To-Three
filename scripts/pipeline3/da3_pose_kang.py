#!/usr/bin/env python3
"""Estimate camera poses for close-viewpoint continuous images via DA3 (no COLMAP).

Runs DA3 inference with extrinsics=None so DA3 predicts the full camera
trajectory itself (c2w convention). Also saves DA3 metric depth maps.

Use case: image sequences shot with very close viewpoints (video-like), where
classic SfM fails due to tiny baselines. DA3's temporal/ray pose estimation is
designed for exactly this.

Outputs:
  <out>/extrinsics.npy    (N,4,4) float32  c2w poses, DA3 convention
  <out>/intrinsics.npy    (N,3,3) float32  input intrinsics (pixel units)
  <out>/pred_intrinsics.npy (N,3,3) float32  DA3 self-estimated intrinsics
  <out>/depths/*.npy      per-image metric depth (resized to original res)
"""
import argparse, os, sys, glob, numpy as np, cv2
os.environ.setdefault("HF_HUB_OFFLINE", "1")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image_dir", required=True)
    p.add_argument("--out_dir", required=True)
    p.add_argument("--focal", type=float, default=1855.0,
                   help="Focal in pixels (from COLMAP on the same camera); cx,cy = image center")
    p.add_argument("--process_res", type=int, default=504)
    p.add_argument("--model_name", default="depth-anything/DA3NESTED-GIANT-LARGE-1.1")
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    image_paths = sorted(glob.glob(os.path.join(args.image_dir, "*.jpg")))
    print(f"images: {len(image_paths)}")

    import torch
    from depth_anything_3.api import DepthAnything3
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"loading model {args.model_name} on {device} ...")
    model = DepthAnything3.from_pretrained(args.model_name).to(device).eval()
    print("model loaded.")

    # Intrinsics: pixel-unit K, cx/cy at image center (same camera for all)
    Ks = []
    for img_path in image_paths:
        h, w = cv2.imread(img_path).shape[:2]
        Ks.append(np.array([[args.focal, 0, w / 2.0],
                            [0, args.focal, h / 2.0],
                            [0, 0, 1]], dtype=np.float32))
    intrinsics = np.stack(Ks)
    print("input intrinsics shape:", intrinsics.shape)

    with torch.no_grad():
        prediction = model.inference(
            image=image_paths,
            extrinsics=None,
            intrinsics=intrinsics,
            use_ray_pose=True,
            align_to_input_ext_scale=True,
            process_res=args.process_res,
            process_res_method="upper_bound_resize",
            export_dir=None,
        )

    exts = np.asarray(prediction.extrinsics, dtype=np.float32)      # (N,4,4) c2w
    pred_ixt = np.asarray(prediction.intrinsics, dtype=np.float32)  # (N,3,3) predicted
    depths = prediction.depth                                        # (N,H,W) metric m
    print("extrinsics shape:", exts.shape, "pred intrinsics shape:", pred_ixt.shape)

    np.save(os.path.join(args.out_dir, "extrinsics.npy"), exts)
    np.save(os.path.join(args.out_dir, "intrinsics.npy"), intrinsics)
    np.save(os.path.join(args.out_dir, "pred_intrinsics.npy"), pred_ixt)

    depth_dir = os.path.join(args.out_dir, "depths")
    os.makedirs(depth_dir, exist_ok=True)
    for j, path in enumerate(image_paths):
        d = depths[j]
        ho, wo = cv2.imread(path).shape[:2]
        if d.shape != (ho, wo):
            d = cv2.resize(d, (wo, ho), interpolation=cv2.INTER_LINEAR)
        np.save(os.path.join(depth_dir, os.path.splitext(os.path.basename(path))[0] + ".npy"),
                d.astype(np.float32))

    # Sanity report: camera centers (c2w translation) should trace a plausible arc.
    print("=== camera centers (c2w t) ===")
    centers = np.zeros((len(image_paths), 3))
    for j, e in enumerate(exts):
        t = e[:3, 3]
        centers[j] = t
        print(f"  {os.path.basename(image_paths[j]):12s} t=({t[0]:+.2f},{t[1]:+.2f},{t[2]:+.2f})")
    if len(centers) > 1:
        # spread of camera centers -> check there is actual motion, and mean center
        ctr = centers.mean(axis=0)
        spread = np.abs(centers - ctr).max(axis=0)
        print(f"  camera-center mean={ctr.round(2)}  max spread=({spread[0]:.2f},{spread[1]:.2f},{spread[2]:.2f})")

    print("=== depth stats (metric m) ===")
    for j, path in enumerate(image_paths):
        d = depths[j]
        print(f"  {os.path.basename(path):12s} min={d.min():.2f} max={d.max():.2f} mean={d.mean():.2f}")

    print("\ndone ->", args.out_dir)


if __name__ == "__main__":
    main()
