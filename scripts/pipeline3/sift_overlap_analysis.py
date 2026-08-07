#!/usr/bin/env python3
"""Analyze pairwise SIFT feature overlap between all images."""
import os, sys, glob
import cv2
import numpy as np

img_dir = sys.argv[1]
files = sorted(glob.glob(os.path.join(img_dir, "*.jpg")))
print(f"images: {len(files)}")

sift = cv2.SIFT_create(nfeatures=4000)
kps, des = [], []
for f in files:
    img = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
    k, d = sift.detectAndCompute(img, None)
    kps.append(k)
    des.append(d)
    print(f"  {os.path.basename(f):12s} {img.shape[1]}x{img.shape[0]} features={len(k)}")

bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
print("\npairwise matches (good ratio matches):")
for i in range(len(files)):
    for j in range(i + 1, len(files)):
        if des[i] is None or des[j] is None:
            continue
        matches = bf.knnMatch(des[i], des[j], k=2)
        good = [m for m, n in matches if m.distance < 0.75 * n.distance] if matches else []
        # also count raw matches
        print(f"  {os.path.basename(files[i]):12s} - {os.path.basename(files[j]):12s}: {len(good)} good matches")
