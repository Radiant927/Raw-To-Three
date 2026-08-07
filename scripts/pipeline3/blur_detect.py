#!/usr/bin/env python3
"""Detect blur / quality issues in images via Laplacian variance."""
import os, sys, glob
import cv2

for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.jpg"))):
    img = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
    lap = cv2.Laplacian(img, cv2.CV_64F).var()
    # variance of raw intensity too
    var = img.var()
    label = "SHARP" if lap > 100 else ("OK" if lap > 50 else "BLURRY")
    print(f"  {os.path.basename(f):12s} laplacian_var={lap:8.1f}  gray_var={var:7.0f}  {label}")
