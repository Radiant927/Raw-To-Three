#!/usr/bin/env python3
"""Verify DA3 pose+depth self-consistency across overlapping image pairs.

For a pair (i,j): unproject image i's depth into 3D via its c2w pose, transform
into image j's camera frame using the relative pose, reproject, and compare
against image j's depth at those pixels. Tests both z-depth (along optical
axis) and radial (Euclidean) interpretations of the depth maps.
"""
import argparse, os, glob, numpy as np, cv2


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out_dir", required=True, help="da3_pose output dir")
    p.add_argument("--image_dir", required=True)
    args = p.parse_args()

    names = sorted(os.path.splitext(os.path.basename(f))[0]
                   for f in glob.glob(os.path.join(args.out_dir, "depths", "*.npy")))
    n = len(names)
    c2w = np.eye(4)[None].repeat(n, axis=0)
    c2w[:, :3, :] = np.load(os.path.join(args.out_dir, "extrinsics.npy"))  # (n,3,4)
    K = np.load(os.path.join(args.out_dir, "intrinsics.npy"))[0]
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    pred_K = np.load(os.path.join(args.out_dir, "pred_intrinsics.npy"))

    print("DA3 self-estimated intrinsics vs input:")
    for j in range(n):
        print(f"  {names[j]:10s} pred fx={pred_K[j,0,0]:6.0f} fy={pred_K[j,1,1]:6.0f} "
              f"cx={pred_K[j,0,2]:5.1f} cy={pred_K[j,1,2]:5.1f}   | input f={fx:.0f} cx={cx:.0f} cy={cy:.0f}")

    depths = {}
    for name in names:
        depths[name] = np.load(os.path.join(args.out_dir, "depths", name + ".npy"))

    # sample every 8th pixel (both axes) to keep it fast
    yy, xx = np.mgrid[0:1920:8, 0:1080:8]
    xx = xx.ravel(); yy = yy.ravel()

    # test pairs: strong-overlap neighbors across the sweep
    idx = {name: i for i, name in enumerate(names)}
    pairs = [(0, 1), (0, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10)]
    # add a few non-adjacent strong pairs
    pairs += [(1, 3), (5, 10), (4, 10), (7, 9)]

    print("\n=== pairwise depth consistency (median relative error) ===")
    for ia, ib in pairs:
        if ia >= n or ib >= n:
            continue
        name_a, name_b = names[ia], names[ib]
        d_a = depths[name_a]; d_b = depths[name_b]
        H, W = d_a.shape
        # relative pose: cam_b = inv(c2w_b) @ c2w_a @ cam_a
        rel = np.linalg.inv(c2w[ib]) @ c2w[ia]
        # rays (un-normalized, z=1) and positions
        u = xx; v = yy  # int indices
        za = d_a[v, u]
        good = za > 0.1
        if not good.any():
            print(f"  {name_a}-{name_b}: no valid pixels")
            continue
        u_g, v_g, z_g = u[good], v[good], za[good]
        uf = u_g.astype(np.float32); vf = v_g.astype(np.float32)
        # interpretation 1: z-depth -> cam_a = [(u-cx)/fx*z, (v-cy)/fy*z, z, 1]
        ray1 = np.stack([(uf - cx) / fx * z_g, (vf - cy) / fy * z_g, z_g, np.ones_like(z_g)], axis=1)
        # interpretation 2: radial depth -> normalize ray
        dir2 = np.stack([(uf - cx) / fx, (vf - cy) / fy, np.ones_like(z_g)], axis=1)
        dir2 = dir2 / np.linalg.norm(dir2, axis=1, keepdims=True)
        ray2 = np.stack([dir2[:, 0] * z_g, dir2[:, 1] * z_g, dir2[:, 2] * z_g, np.ones_like(z_g)], axis=1)
        for label, ray in [("z-depth", ray1), ("radial ", ray2)]:
            cam_b = ray @ rel.T  # (M,4)
            Zb = cam_b[:, 2]
            ok = Zb > 0.05
            if not ok.any():
                print(f"  {name_a}-{name_b} [{label}]: no pos-Z after transform")
                continue
            Xb, Yb = cam_b[ok, 0], cam_b[ok, 1]
            ub = Xb / Zb * fx + cx
            vb = Yb / Zb * fy + cy
            inb = (ub >= 0) & (ub < W) & (vb >= 0) & (vb < H)
            if not inb.any():
                print(f"  {name_a}-{name_b} [{label}]: nothing projects into image b")
                continue
            ub_i = ub[inb].astype(np.int32); vb_i = vb[inb].astype(np.int32)
            db_pred = Zb[inb]
            db_true = d_b[vb_i, ub_i]
            okb = db_true > 0.1
            if not okb.any():
                print(f"  {name_a}-{name_b} [{label}]: no valid target depth")
                continue
            rel_err = np.abs(db_pred[okb] - db_true[okb]) / db_true[okb]
            print(f"  {name_a}-{name_b} [{label}]: median={np.median(rel_err)*100:5.1f}% "
                  f"p90={np.percentile(rel_err,90)*100:6.1f}%  n={okb.sum()}")


if __name__ == "__main__":
    main()
