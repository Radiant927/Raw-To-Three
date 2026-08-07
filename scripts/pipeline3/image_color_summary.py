#!/usr/bin/env python3
"""Per-image color stats: mean RGB, dominant color region, to diagnose scene differences."""
import os, sys, glob
import cv2
import numpy as np

img_dir = sys.argv[1]
for f in sorted(glob.glob(os.path.join(img_dir, "*.jpg"))):
    img = cv2.imread(f)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # overall mean
    mean = img.reshape(-1, 3).mean(axis=0)
    # center region (assume subject is center)
    h, w = img.shape[:2]
    center = img[h//4:3*h//4, w//4:3*w//4]
    cm = center.reshape(-1, 3).mean(axis=0)
    # brightness variance / edge density
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = edges.mean()
    # fraction of sky-ish bright pixels (top region)
    top = img[:h//3].reshape(-1, 3)
    sky_like = ((top > 200).all(axis=1)).mean()
    print(f"  {os.path.basename(f):12s} meanRGB=({mean[0]:.0f},{mean[1]:.0f},{mean[2]:.0f}) "
          f"centerRGB=({cm[0]:.0f},{cm[1]:.0f},{cm[2]:.0f}) edge={edge_density:.3f} skyTop={sky_like:.2f}")
