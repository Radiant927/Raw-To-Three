#!/usr/bin/env python3
"""
Convert 2DGS PLY (61 properties) to 3DGS PLY (62 properties) for SuperSplat viewing.

2DGS has scale_0, scale_1 (surfel disk).
3DGS adds scale_2 (ellipsoid). We set scale_2 = (scale_0 + scale_1) / 2.

Usage:
  python convert_to_3dgs.py --input denoised.ply --output denoised_3dgs.ply
"""
import argparse
import numpy as np
import os
import re


def read_2dgs_ply(path):
    with open(path, 'rb') as f:
        header = b''
        has_scale_2 = False
        while True:
            line = f.readline()
            header += line
            if b'scale_2' in line:
                has_scale_2 = True
            if line.strip() == b'end_header':
                break
        data = f.read()

    if has_scale_2:
        print('  Already 3DGS format (62 properties)')
        return None, None, data, header

    # 2DGS dtype (61 props)
    dt = np.dtype([
        ('x', 'f4'), ('y', 'f4'), ('z', 'f4'),
        ('nx', 'f4'), ('ny', 'f4'), ('nz', 'f4'),
        ('f_dc_0', 'f4'), ('f_dc_1', 'f4'), ('f_dc_2', 'f4'),
    ] + [(f'f_rest_{i}', 'f4') for i in range(45)] + [
        ('opacity', 'f4'),
        ('scale_0', 'f4'), ('scale_1', 'f4'),
        ('rot_0', 'f4'), ('rot_1', 'f4'), ('rot_2', 'f4'), ('rot_3', 'f4'),
    ])
    pts = np.frombuffer(data, dtype=dt)
    return pts, dt, data, header


def write_3dgs_ply(pts, output_path):
    N = len(pts)

    # Build 3DGS dtype (add scale_2)
    dt_3dgs = np.dtype([
        ('x', 'f4'), ('y', 'f4'), ('z', 'f4'),
        ('nx', 'f4'), ('ny', 'f4'), ('nz', 'f4'),
        ('f_dc_0', 'f4'), ('f_dc_1', 'f4'), ('f_dc_2', 'f4'),
    ] + [(f'f_rest_{i}', 'f4') for i in range(45)] + [
        ('opacity', 'f4'),
        ('scale_0', 'f4'), ('scale_1', 'f4'), ('scale_2', 'f4'),
        ('rot_0', 'f4'), ('rot_1', 'f4'), ('rot_2', 'f4'), ('rot_3', 'f4'),
    ])

    out = np.zeros(N, dtype=dt_3dgs)
    for name in dt_3dgs.names:
        if name == 'scale_2':
            # Set to 0 (flat disk) — matches original 2DGS→3DGS conversion
            out[name] = 0.0
        else:
            out[name] = pts[name]

    # Write header
    prop_names = list(dt_3dgs.names)
    with open(output_path, 'wb') as f:
        f.write(b'ply\nformat binary_little_endian 1.0\n')
        f.write(f'element vertex {N}\n'.encode())
        for p in prop_names:
            f.write(f'property float {p}\n'.encode())
        f.write(b'end_header\n')
        out.tofile(f)

    return len(out)


def main():
    parser = argparse.ArgumentParser(description='Convert 2DGS PLY to 3DGS PLY')
    parser.add_argument('--input', required=True, help='Input 2DGS PLY')
    parser.add_argument('--output', required=True, help='Output 3DGS PLY')
    args = parser.parse_args()

    print(f'Reading: {args.input}')
    pts, dt, data, header = read_2dgs_ply(args.input)

    if pts is None:
        # Already 3DGS, just copy
        with open(args.output, 'wb') as f:
            f.write(header)
            f.write(data)
        print(f'  Copied as-is to {args.output}')
        return

    print(f'  {len(pts):,} Gaussians, 2DGS format (61 props)')
    print(f'Writing: {args.output}')
    n = write_3dgs_ply(pts, args.output)
    size_mb = os.path.getsize(args.output) / 1024 / 1024
    print(f'  {n:,} Gaussians, 3DGS format (62 props), {size_mb:.1f} MB')
    print('Done.')


if __name__ == '__main__':
    main()