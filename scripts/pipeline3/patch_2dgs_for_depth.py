#!/usr/bin/env python3
"""Patch 2DGS source to support DA3 depth supervision (monocular depth loss).

Modifies the following files in <gs_dir>:
  - scene/dataset_readers.py: add depth field to CameraInfo, load .npy from depths/
  - scene/cameras.py: add depth parameter to Camera
  - utils/camera_utils.py: pass depth through loadCam
  - arguments/__init__.py: add use_depth_loss flag
  - train.py: add depth loss term in training loop

Idempotent: checks if patches already applied before modifying.
"""
import argparse, os, re, sys


def patch_file(path, transforms, description):
    """Apply list of (old_str, new_str) transforms to file. Skip if already applied."""
    if not os.path.exists(path):
        print(f"  SKIP {description}: {path} not found")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    original = content
    for old_str, new_str in transforms:
        if new_str in content:
            continue  # already applied
        if old_str not in content:
            print(f"  WARNING: pattern not found in {path}: {old_str[:60]}...")
            continue
        content = content.replace(old_str, new_str, 1)
    if content == original:
        print(f"  OK   {description}: already patched or no changes needed")
        return True
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  DONE {description}: patched {path}")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gs_dir", required=True, help="Path to 2d-gs directory")
    args = p.parse_args()

    gs = args.gs_dir.rstrip("/")

    # ── 1. scene/dataset_readers.py ──
    dr = os.path.join(gs, "scene", "dataset_readers.py")
    patch_file(dr, [
        # Add 'depth' to CameraInfo NamedTuple
        (
            "class CameraInfo(NamedTuple):\n    uid: int\n    R: np.array\n    T: np.array\n    FovY: np.array\n    FovX: np.array\n    image: np.array\n    mask: np.array\n    image_path: str\n    image_name: str\n    width: int\n    height: int",
            "class CameraInfo(NamedTuple):\n    uid: int\n    R: np.array\n    T: np.array\n    FovY: np.array\n    FovX: np.array\n    image: np.array\n    mask: np.array\n    depth: np.array\n    image_path: str\n    image_name: str\n    width: int\n    height: int",
        ),
        # Load depth after mask loading in readColmapCameras
        (
            "        # Load mask if available\n        mask = None\n        if masks_folder is not None:\n            mask_path = os.path.join(masks_folder, image_name + \".png\")\n            if os.path.exists(mask_path):\n                mask = Image.open(mask_path).convert(\"L\")\n\n        cam_info = CameraInfo(uid=uid, R=R, T=T, FovY=FovY, FovX=FovX,\n                              image=image, mask=mask,",
            "        # Load mask if available\n        mask = None\n        if masks_folder is not None:\n            mask_path = os.path.join(masks_folder, image_name + \".png\")\n            if os.path.exists(mask_path):\n                mask = Image.open(mask_path).convert(\"L\")\n\n        # Load depth if available (from depths/ subdirectory)\n        depth = None\n        depths_folder = os.path.join(os.path.dirname(images_folder), \"depths\")\n        depth_path = os.path.join(depths_folder, image_name + \".npy\")\n        if os.path.exists(depth_path):\n            depth = np.load(depth_path).astype(np.float32)\n\n        cam_info = CameraInfo(uid=uid, R=R, T=T, FovY=FovY, FovX=FovX,\n                              image=image, mask=mask, depth=depth,",
        ),
        # Fix CameraInfo calls in readCamerasFromTransforms (mask=None → depth=None)
        (
            "            cam_infos.append(CameraInfo(uid=idx, R=R, T=T, FovY=FovY, FovX=FovX,\n                            image=image, mask=None,",
            "            cam_infos.append(CameraInfo(uid=idx, R=R, T=T, FovY=FovY, FovX=FovX,\n                            image=image, mask=None, depth=None,",
        ),
    ], "dataset_readers.py (CameraInfo + depth loading)")

    # Also need to pass depth in the second CameraInfo call for Colmap (readCamerasFromTransforms already has mask=None)
    # And fix the readColmapSceneInfo path for depths_folder (we use parent of images_folder)

    # ── 2. scene/cameras.py ──
    cam = os.path.join(gs, "scene", "cameras.py")
    patch_file(cam, [
        # Add depth parameter to Camera.__init__
        (
            "    def __init__(self, colmap_id, R, T, FoVx, FoVy, image, gt_alpha_mask,\n                 image_name, uid,\n                 trans=np.array([0.0, 0.0, 0.0]), scale=1.0, data_device = \"cuda\"\n                 ):",
            "    def __init__(self, colmap_id, R, T, FoVx, FoVy, image, gt_alpha_mask,\n                 image_name, uid,\n                 trans=np.array([0.0, 0.0, 0.0]), scale=1.0, data_device = \"cuda\",\n                 depth=None\n                 ):",
        ),
        # Store depth as tensor after gt_alpha_mask block
        (
            "        if gt_alpha_mask is not None:\n            self.original_image *= gt_alpha_mask.to(self.data_device)\n        else:\n            self.original_image *= torch.ones((1, self.image_height, self.image_width), device=self.data_device)\n\n        self.zfar = 100.0",
            "        if gt_alpha_mask is not None:\n            self.original_image *= gt_alpha_mask.to(self.data_device)\n        else:\n            self.original_image *= torch.ones((1, self.image_height, self.image_width), device=self.data_device)\n\n        if depth is not None:\n            import torch.nn.functional as F\n            depth_tensor = torch.from_numpy(depth).unsqueeze(0).unsqueeze(0)  # (1,1,H,W)\n            depth_tensor = F.interpolate(depth_tensor, size=(self.image_height, self.image_width), mode='bilinear', align_corners=False)\n            self.depth = depth_tensor.squeeze(0)  # (1, H, W)\n        else:\n            self.depth = None\n\n        self.zfar = 100.0",
        ),
    ], "cameras.py (depth field)")

    # ── 3. utils/camera_utils.py ──
    cu = os.path.join(gs, "utils", "camera_utils.py")
    patch_file(cu, [
        # Pass depth through loadCam to Camera constructor
        (
            "    # Load mask from CameraInfo if available\n    loaded_mask = None\n    if cam_info.mask is not None:\n        loaded_mask = PILtoTorch(cam_info.mask, resolution)\n\n    return Camera(colmap_id=cam_info.uid, R=cam_info.R, T=cam_info.T,\n                  FoVx=cam_info.FovX, FoVy=cam_info.FovY,\n                  image=resized_image_rgb, gt_alpha_mask=loaded_mask,\n                  image_name=cam_info.image_name, uid=id, data_device=args.data_device)",
            "    # Load mask from CameraInfo if available\n    loaded_mask = None\n    if cam_info.mask is not None:\n        loaded_mask = PILtoTorch(cam_info.mask, resolution)\n\n    # Depth is already numpy float32, will be resized in Camera constructor\n    loaded_depth = cam_info.depth\n\n    return Camera(colmap_id=cam_info.uid, R=cam_info.R, T=cam_info.T,\n                  FoVx=cam_info.FovX, FoVy=cam_info.FovY,\n                  image=resized_image_rgb, gt_alpha_mask=loaded_mask,\n                  image_name=cam_info.image_name, uid=id, data_device=args.data_device,\n                  depth=loaded_depth)",
        ),
    ], "camera_utils.py (depth passthrough)")

    # ── 4. arguments/__init__.py ──
    args_file = os.path.join(gs, "arguments", "__init__.py")
    patch_file(args_file, [
        # Add use_depth_loss to PipelineParams
        (
            "class PipelineParams(ParamGroup):\n    def __init__(self, parser):\n        self.convert_SHs_python = False\n        self.compute_cov3D_python = False\n        self.depth_ratio = 0.0\n        self.debug = False\n        super().__init__(parser, \"Pipeline Parameters\")",
            "class PipelineParams(ParamGroup):\n    def __init__(self, parser):\n        self.convert_SHs_python = False\n        self.compute_cov3D_python = False\n        self.depth_ratio = 0.0\n        self.use_depth_loss = False\n        self.debug = False\n        super().__init__(parser, \"Pipeline Parameters\")",
        ),
        # Add lambda_depth to OptimizationParams
        (
            "        self.lambda_dssim = 0.2\n        self.lambda_dist = 100.0\n        self.lambda_normal = 0.05\n        self.opacity_cull = 0.05",
            "        self.lambda_dssim = 0.2\n        self.lambda_dist = 100.0\n        self.lambda_normal = 0.05\n        self.lambda_depth = 1.0\n        self.opacity_cull = 0.05",
        ),
    ], "arguments/__init__.py (use_depth_loss + lambda_depth)")

    # ── 5. train.py ──
    train = os.path.join(gs, "train.py")
    patch_file(train, [
        # Add depth loss weight schedule and depth loss computation
        (
            "        # regularization\n        lambda_normal = opt.lambda_normal if iteration > 7000 else 0.0\n        lambda_dist = opt.lambda_dist if iteration > 3000 else 0.0",
            "        # regularization\n        lambda_normal = opt.lambda_normal if iteration > 7000 else 0.0\n        lambda_dist = opt.lambda_dist if iteration > 3000 else 0.0\n        lambda_depth = opt.lambda_depth if iteration > 3000 and pipe.use_depth_loss else 0.0",
        ),
        # Add depth loss after dist/normal losses
        (
            "        # loss\n        total_loss = loss + dist_loss + normal_loss\n\n        total_loss.backward()",
            "        # Depth supervision loss (DA3 metric depth)\n        depth_loss_val = torch.tensor(0.0, device=\"cuda\")\n        if lambda_depth > 0 and viewpoint_cam.depth is not None:\n            surf_depth = render_pkg[\"surf_depth\"]\n            gt_depth = viewpoint_cam.depth.cuda()\n            valid = (gt_depth > 0.01) & (gt_depth < 200.0)\n            if valid.any():\n                depth_loss_val = lambda_depth * torch.abs(surf_depth[valid] - gt_depth[valid]).mean()\n\n        # loss\n        total_loss = loss + dist_loss + normal_loss + depth_loss_val\n\n        total_loss.backward()",
        ),
    ], "train.py (depth loss term)")

    print("\nPatch complete. Verify the changes above before training.")


if __name__ == "__main__":
    main()
