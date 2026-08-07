#!/usr/bin/env python3
"""Run DA3 metric depth prediction on undistorted images with COLMAP poses.

Outputs per-image depth maps (.npy float32) in COLMAP metric scale.
DA3 is conditioned on COLMAP w2c extrinsics and PINHOLE intrinsics, with
align_to_input_ext_scale=True so output depth matches COLMAP scale.

Expected input structure:
  <colmap_dir>/sparse/0/          — COLMAP binary reconstruction
  <colmap_dir>/images/            — undistorted images (PNG/JPG)
  <colmap_dir>/depths/            — output directory for .npy depth maps

Depth maps are resized to match the original undistorted image resolution.
"""
import argparse, os, sys, numpy as np, cv2
os.environ.setdefault("HF_HUB_OFFLINE", "1")  # 离线加载 DA3 缓存权重
from PIL import Image
import pycolmap


def build_w2c(img):
    """Build 4x4 world-to-camera matrix from pycolmap Image object."""
    pose = img.cam_from_world()
    M = pose.matrix()  # 3x4 [R|t]
    w2c = np.eye(4, dtype=np.float64)
    w2c[:3, :] = M
    return w2c


def build_k(cam):
    """Build 3x3 K matrix from pycolmap Camera (SIMPLE_PINHOLE or PINHOLE)."""
    model = cam.model_name
    if model == "SIMPLE_PINHOLE":
        f, cx, cy = cam.params
        fx, fy = f, f
    elif model == "PINHOLE":
        fx, fy, cx, cy = cam.params
    else:
        raise ValueError(f"Unsupported camera model: {model}")
    return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float64)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--colmap_dir", required=True, help="COLMAP dir with sparse/0/ and images/")
    p.add_argument("--model_name", default="depth-anything/DA3NESTED-GIANT-LARGE-1.1",
                   help="DA3 model name or local path")
    p.add_argument("--process_res", type=int, default=504, help="DA3 processing resolution")
    p.add_argument("--batch_size", type=int, default=4, help="Batch size for DA3 inference")
    p.add_argument("--depth_dirname", default="depths", help="Output subdirectory name")
    args = p.parse_args()

    sparse0 = os.path.join(args.colmap_dir, "sparse", "0")
    img_dir = os.path.join(args.colmap_dir, "images")
    depth_dir = os.path.join(args.colmap_dir, args.depth_dirname)
    os.makedirs(depth_dir, exist_ok=True)

    # Load COLMAP reconstruction
    recon = pycolmap.Reconstruction(sparse0)
    print(f"Loaded reconstruction: {recon.num_reg_images()} images, {recon.num_points3D()} points")

    # Collect all registered images sorted by name
    reg_imgs = []
    for img_id in sorted(recon.images.keys()):
        img = recon.images[img_id]
        cam = recon.cameras[img.camera_id]
        img_path = os.path.join(img_dir, img.name)
        if not os.path.exists(img_path):
            for ext in ['.png', '.jpg', '.PNG', '.JPG', '.jpeg']:
                alt = os.path.join(img_dir, os.path.splitext(img.name)[0] + ext)
                if os.path.exists(alt):
                    img_path = alt
                    break
        if not os.path.exists(img_path):
            print(f"  WARNING: image not found for {img.name}, skipping")
            continue
        reg_imgs.append((img, cam, img_path))

    print(f"Found {len(reg_imgs)} registered images with files")

    # Build extrinsics (w2c) and intrinsics (K) arrays
    image_paths = []
    extrinsics = []
    intrinsics = []
    image_names = []

    for img, cam, img_path in reg_imgs:
        w2c = build_w2c(img)
        K = build_k(cam)
        extrinsics.append(w2c)
        intrinsics.append(K)
        image_paths.append(img_path)
        image_names.append(os.path.splitext(os.path.basename(img.name))[0] + ".npy")

    extrinsics = np.stack(extrinsics).astype(np.float32)  # (N, 4, 4)
    intrinsics = np.stack(intrinsics).astype(np.float32)  # (N, 3, 3)

    print(f"Extrinsics shape: {extrinsics.shape}, Intrinsics shape: {intrinsics.shape}")

    # Load DA3 model
    import torch
    from depth_anything_3.api import DepthAnything3

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading DA3 model: {args.model_name} on {device}")
    model = DepthAnything3.from_pretrained(args.model_name).to(device).eval()
    print("Model loaded.")

    # Umeyama scale alignment needs the full trajectory, so run all images
    # in a single inference call (small batches break pose covariance).
    n = len(image_paths)
    print(f"  Running single inference over all {n} images (process_res={args.process_res})")

    with torch.no_grad():
        prediction = model.inference(
            image=image_paths,
            extrinsics=extrinsics,
            intrinsics=intrinsics,
            use_ray_pose=True,
            align_to_input_ext_scale=True,
            process_res=args.process_res,
            process_res_method="upper_bound_resize",
            export_dir=None,
        )

    depths = prediction.depth  # (N, H_proc, W_proc) float32, metric in meters

    for j, name in enumerate(image_names):
        depth_proc = depths[j]  # (H_proc, W_proc)
        # Resize to original image resolution
        orig_img = cv2.imread(image_paths[j])
        h_orig, w_orig = orig_img.shape[:2]
        h_proc, w_proc = depth_proc.shape

        if (h_proc, w_proc) != (h_orig, w_orig):
            depth_out = cv2.resize(depth_proc, (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)
        else:
            depth_out = depth_proc

        out_path = os.path.join(depth_dir, name)
        np.save(out_path, depth_out.astype(np.float32))

        if j % 10 == 0:
            print(f"    saved {j+1}/{n}")
            sys.stdout.flush()

    print(f"\nDone: {n} depth maps saved to {depth_dir}/")

    # Quick stats
    sample = np.load(os.path.join(depth_dir, image_names[0]))
    print(f"  Sample depth ({image_names[0]}): shape={sample.shape}, "
          f"min={sample.min():.2f}m, max={sample.max():.2f}m, mean={sample.mean():.2f}m")


if __name__ == "__main__":
    main()
