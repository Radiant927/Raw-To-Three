#!/usr/bin/env python3
"""
Denoise 2DGS/3DGS PLY using opacity + statistical + radius outlier removal.
Removes floaters and isolated noise while preserving building structure.

Supports both binary (2DGS/3DGS) and ASCII PLY input.
For binary input, preserves all attributes (colors, scales, rotations, etc.).
For ASCII input, reads XYZ and outputs XYZ.

Usage:
  python denoise.py --input raw.ply --output clean.ply
  python denoise.py --input raw.ply --output clean.ply --nb_neighbors 30 --std_ratio 1.5
"""
import argparse
import numpy as np
import os
import sys


def read_ply(path):
    """Read PLY and return (xyz_array, format_info).

    For binary PLY: returns full structured array + keeps format info for rewrite.
    For ASCII PLY: returns just XYZ.
    """
    # Try ASCII first
    try:
        with open(path, 'r') as f:
            header = []
            while True:
                line = f.readline()
                header.append(line)
                if line.strip() == 'end_header':
                    break
        prop_count = sum(1 for h in header if h.startswith('property float'))
        cols = list(range(min(3, prop_count)))
        data = np.loadtxt(path, skiprows=len(header), usecols=cols)
        return data[:, :3], None  # (xyz, None) signals ASCII
    except:
        pass

    # Binary PLY
    with open(path, 'rb') as f:
        header_bytes = b''
        prop_names = []
        while True:
            line = f.readline()
            header_bytes += line
            if line.startswith(b'property'):
                prop_names.append(line.decode().strip())
            if line.strip() == b'end_header':
                break
        data = f.read()

    # Parse property names to build dtype
    dtype_fields = []
    for p in prop_names:
        parts = p.split()
        if len(parts) >= 3 and parts[0] == 'property' and parts[1] == 'float':
            dtype_fields.append((parts[2], 'f4'))

    if not dtype_fields:
        raise ValueError(f"Cannot parse properties from: {path}")

    dt = np.dtype(dtype_fields)
    pts = np.frombuffer(data, dtype=dt)

    # Extract XYZ (first 3 fields)
    xyz_names = [f[0] for f in dtype_fields[:3]]
    xyz = np.column_stack([pts[n] for n in xyz_names])

    return xyz, {'data': pts, 'dtype': dt, 'header': header_bytes, 'prop_names': dtype_fields}


def denoise_open3d(xyz, nb_neighbors=30, std_ratio=1.5, radius=0.05, min_neighbors=10):
    """Apply statistical + radius outlier removal. Returns mask of inliers (bool over input xyz)."""
    import open3d as o3d

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)

    # Step 1: Statistical outlier removal
    _, stat_indices = pcd.remove_statistical_outlier(
        nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    stat_mask = np.zeros(len(xyz), dtype=bool)
    stat_mask[stat_indices] = True

    # Step 2: Radius outlier removal on the survivors
    xyz_filtered = xyz[stat_mask]
    pcd2 = o3d.geometry.PointCloud()
    pcd2.points = o3d.utility.Vector3dVector(xyz_filtered)
    _, rad_indices = pcd2.remove_radius_outlier(
        nb_points=min_neighbors, radius=radius)
    rad_mask_local = np.zeros(len(xyz_filtered), dtype=bool)
    rad_mask_local[rad_indices] = True

    # Combine: final mask over original xyz
    final_mask = np.zeros(len(xyz), dtype=bool)
    stat_idx_arr = np.where(stat_mask)[0]
    final_mask[stat_idx_arr[rad_mask_local]] = True
    return final_mask


def main():
    parser = argparse.ArgumentParser(description='Denoise 3DGS/2DGS PLY')
    parser.add_argument('--input', required=True, help='Input PLY path')
    parser.add_argument('--output', required=True, help='Output PLY path')
    parser.add_argument('--opacity_min', type=float, default=0.09,
                        help='Min opacity (sigmoid) to keep (default: 0.09). Set 0 to disable.')
    parser.add_argument('--nb_neighbors', type=int, default=30,
                        help='Statistical: neighbors to consider (default: 30)')
    parser.add_argument('--std_ratio', type=float, default=1.5,
                        help='Statistical: std deviation threshold (default: 1.5)')
    parser.add_argument('--radius', type=float, default=0.05,
                        help='Radius filter: search radius in meters (default: 0.05)')
    parser.add_argument('--min_neighbors', type=int, default=10,
                        help='Radius filter: min neighbors within radius (default: 10)')
    parser.add_argument('--max_scale', type=float, default=0.0,
                        help='Max Gaussian scale in meters (default: 0.0 = disabled). Halos are cleaned by opacity+density filters.')
    args = parser.parse_args()

    print(f'Reading: {args.input}')
    xyz, fmt_info = read_ply(args.input)
    n_in = len(xyz)
    is_binary = fmt_info is not None
    print(f'  {n_in:,} points ({"binary" if is_binary else "ASCII"})')

    # Opacity pre-filter (binary + has opacity field only)
    keep_indices = np.arange(n_in)
    if is_binary and args.opacity_min > 0 and 'opacity' in fmt_info['dtype'].names:
        op_sig = 1.0 / (1.0 + np.exp(-fmt_info['data']['opacity']))
        op_mask = op_sig > args.opacity_min
        n_before = len(keep_indices)
        keep_indices = keep_indices[op_mask]
        removed = n_before - len(keep_indices)
        print(f'  Opacity filter (>{args.opacity_min:.3f}): {removed:,} removed ({removed / n_before * 100:.1f}%)')
        xyz = xyz[op_mask]

    print(f'\nDenoising: nb_neighbors={args.nb_neighbors}, std_ratio={args.std_ratio}, '
          f'radius={args.radius}, min_neighbors={args.min_neighbors}')
    denoise_mask = denoise_open3d(
        xyz, args.nb_neighbors, args.std_ratio, args.radius, args.min_neighbors)
    keep_indices = keep_indices[denoise_mask]
    n_after_denoise = len(keep_indices)
    removed = n_in - n_after_denoise
    print(f'  {n_after_denoise:,} points kept, {removed:,} removed ({removed / n_in * 100:.1f}%)')

    n_out = n_after_denoise
    if is_binary:
        clean_data = fmt_info['data'][keep_indices]
        if args.max_scale > 0 and 'scale_0' in fmt_info['dtype'].names:
            s0 = np.exp(clean_data['scale_0'])
            s1 = np.exp(clean_data['scale_1'])
            scale_mask = (s0 <= args.max_scale) & (s1 <= args.max_scale)
            n_before = len(clean_data)
            clean_data = clean_data[scale_mask]
            n_out = len(clean_data)
            scale_removed = n_before - n_out
            print(f'  Scale filter (> {args.max_scale:.2f}m): {scale_removed:,} removed ({scale_removed / n_before * 100:.1f}%)')

    print(f'\nWriting: {args.output}')
    if is_binary:
        import re
        header_str = re.sub(
            b'element vertex \\d+',
            f'element vertex {n_out}'.encode(),
            fmt_info['header'])
        with open(args.output, 'wb') as f:
            f.write(header_str)
            clean_data.tofile(f)
    else:
        clean_xyz = xyz[denoise_mask]
        with open(args.output, 'w') as f:
            f.write('ply\nformat ascii 1.0\n')
            f.write(f'element vertex {n_out}\n')
            f.write('property float x\nproperty float y\nproperty float z\n')
            f.write('end_header\n')
            for i in range(n_out):
                f.write(f'{clean_xyz[i, 0]:.6f} {clean_xyz[i, 1]:.6f} {clean_xyz[i, 2]:.6f}\n')

    size_mb = os.path.getsize(args.output) / 1024 / 1024
    print(f'  {size_mb:.1f} MB')
    print('Done.')


if __name__ == '__main__':
    main()
