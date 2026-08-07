#!/usr/bin/env python3
"""Post-training opacity-only filter for 2DGS PLY.

Applies sigmoid(opacity) >= threshold to remove low-opacity floaters.
No DBSCAN, no SOR — just a simple opacity cutoff as specified in pipeline V2.
"""
import argparse, os, numpy as np
from plyfile import PlyData, PlyElement


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Input 2DGS PLY path")
    p.add_argument("--output", required=True, help="Output filtered PLY path")
    p.add_argument("--opacity_min", type=float, default=0.09, help="sigmoid(opacity) threshold")
    args = p.parse_args()

    ply = PlyData.read(args.input)
    verts = ply["vertex"]
    n_before = len(verts)

    opacity_logit = verts["opacity"]
    opacity_actual = sigmoid(opacity_logit)
    keep = opacity_actual >= args.opacity_min

    print(f"Before: {n_before:,} Gaussians")
    print(f"Opacity range: {opacity_actual.min():.4f} - {opacity_actual.max():.4f}, mean={opacity_actual.mean():.4f}")
    print(f"Keeping {keep.sum():,} / {n_before:,} ({100*keep.sum()/n_before:.1f}%) with sigmoid(opacity) >= {args.opacity_min}")

    # Build filtered vertex data
    prop_names = [p.name for p in verts.properties]
    dtype = [(n, verts[n].dtype) for n in prop_names]
    filtered = np.empty(keep.sum(), dtype=dtype)
    for n in prop_names:
        filtered[n] = verts[n][keep]

    # Write output
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    el = PlyElement.describe(filtered, "vertex")
    PlyData([el], text=False).write(args.output)
    print(f"Written: {args.output} ({os.path.getsize(args.output)/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()
