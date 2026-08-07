#!/usr/bin/env python3
"""
Export selected Gaussians from 2DGS PLY as colored ASCII PLY for Blender.

Usage:
  python export_for_blender.py --input denoised.ply --output walls.ply --z_min 1.0
  python export_for_blender.py --input denoised.ply --output roof.ply --z_min 2.5
"""
import argparse
import numpy as np
import os
import sys

SH_C0 = 0.28209479177387814


def read_2dgs_ply(path):
    with open(path, 'rb') as f:
        while f.readline().strip() != b'end_header':
            pass
        data = f.read()

    dt = np.dtype([
        ('x', 'f4'), ('y', 'f4'), ('z', 'f4'),
        ('nx', 'f4'), ('ny', 'f4'), ('nz', 'f4'),
        ('f_dc_0', 'f4'), ('f_dc_1', 'f4'), ('f_dc_2', 'f4'),
    ] + [(f'f_rest_{i}', 'f4') for i in range(45)] + [
        ('opacity', 'f4'),
        ('scale_0', 'f4'), ('scale_1', 'f4'),
        ('rot_0', 'f4'), ('rot_1', 'f4'), ('rot_2', 'f4'), ('rot_3', 'f4'),
    ])
    return np.frombuffer(data, dtype=dt)


def sh_dc_to_rgb(f_dc):
    rgb = np.clip((f_dc * SH_C0 + 0.5) * 255, 0, 255).astype(np.uint8)
    return rgb[:, 0], rgb[:, 1], rgb[:, 2]


def main():
    parser = argparse.ArgumentParser(description='Export 2DGS PLY subset for Blender')
    parser.add_argument('--input', required=True, help='Input 2DGS PLY')
    parser.add_argument('--output', required=True, help='Output ASCII PLY')
    parser.add_argument('--z_min', type=float, default=1.0,
                        help='Min Z height in meters (default: 1.0)')
    parser.add_argument('--z_max', type=float, default=float('inf'),
                        help='Max Z height in meters')
    parser.add_argument('--x_min', type=float, default=-float('inf'))
    parser.add_argument('--x_max', type=float, default=float('inf'))
    parser.add_argument('--y_min', type=float, default=-float('inf'))
    parser.add_argument('--y_max', type=float, default=float('inf'))
    parser.add_argument('--no_color', action='store_true',
                        help='Export XYZ only, no RGB')
    args = parser.parse_args()

    print(f'Reading: {args.input}')
    pts = read_2dgs_ply(args.input)
    print(f'  {len(pts):,} Gaussians')

    mask = (
        (pts['z'] >= args.z_min) & (pts['z'] <= args.z_max) &
        (pts['x'] >= args.x_min) & (pts['x'] <= args.x_max) &
        (pts['y'] >= args.y_min) & (pts['y'] <= args.y_max)
    )
    subset = pts[mask]
    print(f'  {len(subset):,} selected (Z∈[{args.z_min}, {args.z_max}])')
    print(f'  X: [{subset["x"].min():.2f}, {subset["x"].max():.2f}]')
    print(f'  Y: [{subset["y"].min():.2f}, {subset["y"].max():.2f}]')
    print(f'  Z: [{subset["z"].min():.2f}, {subset["z"].max():.2f}]')

    N = len(subset)
    with open(args.output, 'w') as f:
        if args.no_color:
            f.write('ply\nformat ascii 1.0\n')
            f.write(f'element vertex {N}\n')
            f.write('property float x\nproperty float y\nproperty float z\n')
            f.write('end_header\n')
            for i in range(N):
                f.write(f'{subset["x"][i]:.6f} {subset["y"][i]:.6f} {subset["z"][i]:.6f}\n')
        else:
            r, g, b = sh_dc_to_rgb(np.column_stack([
                subset['f_dc_0'], subset['f_dc_1'], subset['f_dc_2']]))
            f.write('ply\nformat ascii 1.0\n')
            f.write(f'element vertex {N}\n')
            f.write('property float x\nproperty float y\nproperty float z\n')
            f.write('property uchar red\nproperty uchar green\nproperty uchar blue\n')
            f.write('end_header\n')
            for i in range(N):
                f.write(f'{subset["x"][i]:.6f} {subset["y"][i]:.6f} {subset["z"][i]:.6f} '
                        f'{r[i]} {g[i]} {b[i]}\n')

    size_mb = os.path.getsize(args.output) / 1024 / 1024
    print(f'Saved: {args.output} ({size_mb:.1f} MB)')


if __name__ == '__main__':
    main()
