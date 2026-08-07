#!/usr/bin/env python3
"""Decisive check: are DA3 pose+depth coherent at real SIFT correspondences?

For each matched feature pair (p in img_i <-> q in img_j):
  - unproject p through depth_i + c2w_i -> world P
  - unproject q through depth_j + c2w_j -> world Q
If DA3's trajectory + depth are self-consistent, P ~ Q for statue surface
points. Tests both z-depth and radial-depth interpretations of the depth maps.
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

    def matches(i, j):
        bf = cv2.BFMatcher(cv2.NORM_L2)
        m12 = bf.knnMatch(dess[i], dess[j], k=2)
        good = []
        for m, nn in m12:
            if m.distance < 0.75 * nn.distance:
                good.append(m)
        return good

    pairs = []
    for a in range(n - 1):
        pairs.append((a, a + 1))
    pairs += [(0, 2), (1, 3), (4, 6), (5, 10), (7, 9), (4, 10)]

    print("=== matched-point world consistency (median |P-Q| / depth) ===")
    for i, j in pairs:
        good = matches(i, j)
        if len(good) < 20:
            print(f"  {names[i]}-{names[j]}: only {len(good)} matches, skip")
            continue
        pts_i = np.float32([kps[i][m.queryIdx].pt for m in good])
        pts_j = np.float32([kps[j][m.trainIdx].pt for m in good])
        d_i = depths[i]; d_j = depths[j]
        for label, mode in [("z-depth", 0), ("radial ", 1)]:
            rels = []
            for (u1, v1), (u2, v2) in zip(pts_i, pts_j):
                u1 = int(round(u1)); v1 = int(round(v1))
                u2 = int(round(u2)); v2 = int(round(v2))
                z1 = d_i[v1, u1]; z2 = d_j[v2, u2]
                if z1 < 0.1 or z2 < 0.1 or z1 > args.max_depth or z2 > args.max_depth:
                    continue
                if mode == 0:
                    p1 = np.array([(u1 - cx) / fx * z1, (v1 - cy) / fy * z1, z1])
                    p2 = np.array([(u2 - cx) / fx * z2, (v2 - cy) / fy * z2, z2])
                else:
                    d1 = np.array([(u1 - cx) / fx, (v1 - cy) / fy, 1.0]); d1 /= np.linalg.norm(d1)
                    d2 = np.array([(u2 - cx) / fx, (v2 - cy) / fy, 1.0]); d2 /= np.linalg.norm(d2)
                    p1 = d1 * z1; p2 = d2 * z2
                P = (c2w[i] @ np.append(p1, 1))[:3]
                Q = (c2w[j] @ np.append(p2, 1))[:3]
                rels.append(np.linalg.norm(P - Q) / max(z1, z2))
            if rels:
                rels = np.array(rels)
                print(f"  {names[i]:8s}-{names[j]:8s} [{label}]: n={len(rels):5d} "
                      f"median={np.median(rels)*100:6.1f}%  p90={np.percentile(rels,90)*100:6.1f}%")


if __name__ == "__main__":
    main()
