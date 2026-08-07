#!/usr/bin/env python3
"""Find the camera-frame convention under which DA3 pose+depth are self-consistent.

Tests 8 sign conventions on the camera coordinates (x/y/z flips) applied before
the c2w transform. If any convention yields uniformly low P-vs-Q error across
ALL pairs (not just near-duplicates), that convention is correct and the DA3
trajectory is usable as camera poses.
"""
import argparse, os, glob, numpy as np, cv2


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out_dir", required=True)
    p.add_argument("--image_dir", required=True)
    p.add_argument("--max_depth", type=float, default=30.0)
    args = p.parse_args()

    img_paths = sorted(glob.glob(os.path.join(args.image_dir, "*.jpg")))
    names = [os.path.splitext(os.path.basename(x))[0] for x in img_paths]
    n = len(img_paths)
    c2w = np.eye(4)[None].repeat(n, axis=0)
    c2w[:, :3, :] = np.load(os.path.join(args.out_dir, "extrinsics.npy"))
    K = np.load(os.path.join(args.out_dir, "intrinsics.npy"))[0]
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    depth_dir = os.path.join(args.out_dir, "depths")

    depths = [np.load(os.path.join(depth_dir, nm + ".npy")) for nm in names]
    imgs = [cv2.imread(pth, cv2.IMREAD_GRAYSCALE) for pth in img_paths]
    sift = cv2.SIFT_create(nfeatures=4000)
    kps, dess = [], []
    for im in imgs:
        k, d = sift.detectAndCompute(im, None)
        kps.append(k); dess.append(d)

    pairs = [(a, a + 1) for a in range(n - 1)] + [(0, 2), (4, 10), (7, 9)]

    # precompute matches + per-pair depth samples
    pair_data = []
    for i, j in pairs:
        bf = cv2.BFMatcher(cv2.NORM_L2)
        m12 = bf.knnMatch(dess[i], dess[j], k=2)
        good = [m for m, nn in m12 if m.distance < 0.75 * nn.distance]
        if len(good) < 15:
            continue
        pts = []
        for m in good:
            u1, v1 = kps[i][m.queryIdx].pt
            u2, v2 = kps[j][m.trainIdx].pt
            z1 = depths[i][int(round(v1)), int(round(u1))]
            z2 = depths[j][int(round(v2)), int(round(u2))]
            if z1 < 0.1 or z2 < 0.1 or z1 > args.max_depth or z2 > args.max_depth:
                continue
            # raw camera-frame points using normalized coords * z
            p1 = np.array([(u1 - cx) / fx * z1, (v1 - cy) / fy * z1, z1])
            p2 = np.array([(u2 - cx) / fx * z2, (v2 - cy) / fy * z2, z2])
            pts.append((p1, p2, max(z1, z2)))
        if len(pts) >= 15:
            pair_data.append((names[i], names[j], pts))

    print(f"{len(pair_data)} pairs used, {sum(len(p) for _,_,p in pair_data)} matches")
    print("convention (sx,sy,sz) | per-pair median rel err [%]  (worst pair = max)")
    rows = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                S = np.diag([sx, sy, sz, 1.0])
                meds = []
                for na, nb, pts in pair_data:
                    i = names.index(na); j = names.index(nb)
                    rels = []
                    for p1, p2, zmax in pts:
                        P = (c2w[i] @ (S @ np.append(p1, 1)))[:3]
                        Q = (c2w[j] @ (S @ np.append(p2, 1)))[:3]
                        rels.append(np.linalg.norm(P - Q) / zmax)
                    meds.append(np.median(rels) * 100)
                if meds:
                    rows.append(((sx, sy, sz), meds))
    # sort by worst pair error (best convention first)
    rows.sort(key=lambda r: max(r[1]))
    for (sx, sy, sz), meds in rows:
        m = ",".join(f"{x:5.1f}" for x in meds)
        print(f"  ({sx:+d},{sy:+d},{sz:+d})      worst={max(meds):5.1f}  med={np.median(meds):5.1f}  [{m}]")


if __name__ == "__main__":
    main()
