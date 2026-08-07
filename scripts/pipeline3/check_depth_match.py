#!/usr/bin/env python3
"""Verify that every COLMAP image has a matching depth file for 2DGS training.

2DGS builds image_name = basename(extr.name).split('.')[0], then expects
<data>/depths/<image_name>.npy. We replicate exactly that logic here.
"""
import os, sys, glob

data_dir = sys.argv[1]
from scene.colmap_loader import read_extrinsics_binary
from scene.dataset_readers import readColmapCameras  # uses patched code

import numpy as np

sparse0 = os.path.join(data_dir, "sparse", "0")
images_folder = os.path.join(data_dir, "images")
depths_folder = os.path.join(data_dir, "depths")

cam_extrinsics = read_extrinsics_binary(os.path.join(sparse0, "images.bin"))
cam_intrinsics = read_extrinsics_binary  # dummy, not used here

# Replicate readColmapCameras image_name logic
missing = []
depth_paths = set(os.listdir(depths_folder))
for key, extr in cam_extrinsics.items():
    image_path = os.path.join(images_folder, os.path.basename(extr.name))
    image_name = os.path.basename(image_path).split('.')[0]
    depth_path = os.path.join(depths_folder, image_name + ".npy")
    if os.path.basename(depth_path) not in depth_paths:
        missing.append((extr.name, image_name + ".npy"))

if missing:
    print(f"MISSING {len(missing)} depth files:")
    for orig, want in missing[:20]:
        print(f"  {orig}  ->  wants {want}")
else:
    print(f"OK: all {len(cam_extrinsics)} images have matching depth files")
