#!/usr/bin/env python3
"""Diagnose why SfM fails on an image set: epipolar vs homography inliers.

For every pair: SIFT match -> count essential-matrix inliers (real 3D
parallax geometry) and homography inliers (planar/rotational scene).
  * many E-inliers  -> real baseline, SfM should work; problem is tooling/config
  * many H-inliers, few E-inliers -> rotation/planar, no baseline
  * few of both -> texture/overlap too weak
Also reports the relative translation magnitude recovered by recoverPose.
"""
import argparse, os, glob, numpy as np, cv2, itertools


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image_dir", required=True)
    p.add_argument("--focal", type=float, default=1855.0)
    p.add_argument("--nfeatures", type=int, default=8000)
    args = p.parse_args()

    img_paths = sorted(glob.glob(os.path.join(args.image_dir, "*.jpg")))
    names = [os.path.splitext(os.path.basename(x))[0] for x in img_paths]
    n = len(img_paths)
    imgs = [cv2.imread(pth, cv2.IMREAD_GRAYSCALE) for pth in img_paths]
    sift = cv2.SIFT_create(nfeatures=args.nfeatures)
    kps, dess = [], []
    for im in imgs:
        k, d = sift.detectAndCompute(im, None)
        kps.append(k); dess.append(d)

    h0, w0 = imgs[0].shape
    K = np.array([[args.focal, 0, w0 / 2], [0, args.focal, h0 / 2], [0, 0, 1]], dtype=np.float64)

    print(f"{len(img_paths)} images, K(f={args.focal}), nfeatures={args.nfeatures}")
    print(f"{'pair':14s} {'nM':>4s} {'Einl':>5s} {'Hinl':>5s} {'t_norm':>7s}  verdict")
    for i, j in itertools.combinations(range(n), 2):
        bf = cv2.BFMatcher(cv2.NORM_L2)
        m12 = bf.knnMatch(dess[i], dess[j], k=2)
        good = [m for m, nn in m12 if m.distance < 0.75 * nn.distance]
        nm = len(good)
        if nm < 8:
            print(f"  {names[i]}-{names[j]:8s} {nm:4d}  {'-':>5s} {'-':>5s} {'-':>7s}  too few matches")
            continue
        p1 = np.float32([kps[i][m.queryIdx].pt for m in good])
        p2 = np.float32([kps[j][m.trainIdx].pt for m in good])
        # essential (real parallax geometry)
        E, maskE = cv2.findEssentialMat(p1, p2, K, method=cv2.RANSAC, prob=0.999, threshold=2.0)
        nE = int(maskE.sum()) if maskE is not None else 0
        # homography (rotation / planar)
        H, maskH = cv2.findHomography(p1, p2, cv2.RANSAC, 3.0)
        nH = int(maskH.sum()) if maskH is not None else 0
        # translation magnitude from recoverPose (needs >= 8 inliers)
        tmag = float("nan")
        if nE >= 8:
            _, R, t, _ = cv2.recoverPose(E, p1[maskE.ravel() == 1], p2[maskE.ravel() == 1], K)
            tmag = np.linalg.norm(t)
        if nE >= 30 and nE >= 0.5 * nm:
            verdict = "STRONG baseline"
        elif nE >= 15:
            verdict = "OK baseline"
        elif nH >= 0.6 * nm and nE < 0.15 * nm:
            verdict = "ROTATION/PLANAR?"
        elif nE < 15:
            verdict = "weak/ambiguous"
        else:
            verdict = "weak"
        print(f"  {names[i]}-{names[j]:8s} {nm:4d} {nE:5d} {nH:5d} {tmag:7.3f}  {verdict}")


if __name__ == "__main__":
    main()
