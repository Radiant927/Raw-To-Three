#!/usr/bin/env python3
"""
Export 2DGS PLY as colored GLB mesh for Blender/3D software.

Uses Poisson surface reconstruction to create a proper mesh from the
point cloud, then colors mesh vertices from nearest Gaussians.

Usage:
  python export_glb.py --input denoised.ply --output model.glb
  python export_glb.py --input denoised.ply --output walls.glb --z_min 1.0
  python export_glb.py --input denoised.ply --output walls.glb --z_min 1.0 --method quad
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


def sh_to_rgb(f_dc_0, f_dc_1, f_dc_2):
    """Convert SH DC coefficients to 0-1 float RGB."""
    rgb = np.zeros((len(f_dc_0), 3), dtype=np.float64)
    rgb[:, 0] = np.clip(f_dc_0 * SH_C0 + 0.5, 0, 1)
    rgb[:, 1] = np.clip(f_dc_1 * SH_C0 + 0.5, 0, 1)
    rgb[:, 2] = np.clip(f_dc_2 * SH_C0 + 0.5, 0, 1)
    return rgb


def export_poisson(xyz, rgb, output_path, depth=10):
    """Poisson surface reconstruction → colored mesh → GLB."""
    import open3d as o3d
    from scipy.spatial import KDTree

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz.astype(np.float64))
    pcd.colors = o3d.utility.Vector3dVector(rgb.astype(np.float64))

    # Estimate normals
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
    pcd.orient_normals_consistent_tangent_plane(100)

    # Poisson reconstruction
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=depth, width=0, scale=1.1, linear_fit=True)

    # Remove low-density vertices (noise)
    densities_np = np.asarray(densities)
    density_threshold = np.percentile(densities_np, 5)
    vertices_to_remove = densities_np < density_threshold
    mesh.remove_vertices_by_mask(vertices_to_remove)

    # Color mesh vertices from nearest point cloud points
    mesh_xyz = np.asarray(mesh.vertices)
    tree = KDTree(xyz)
    _, idx = tree.query(mesh_xyz)
    mesh.vertex_colors = o3d.utility.Vector3dVector(rgb[idx].astype(np.float64))

    # Export
    o3d.io.write_triangle_mesh(output_path, mesh, write_vertex_colors=True)
    return len(mesh.vertices), len(mesh.triangles)


def main():
    parser = argparse.ArgumentParser(
        description='Export 2DGS PLY as colored GLB mesh')
    parser.add_argument('--input', required=True, help='Input 2DGS PLY')
    parser.add_argument('--output', required=True, help='Output GLB file')
    parser.add_argument('--method', default='poisson',
                        choices=['poisson', 'quad'],
                        help='Reconstruction method (default: poisson)')
    parser.add_argument('--depth', type=int, default=10,
                        help='Poisson depth (default: 10, higher = more detail)')
    parser.add_argument('--quad_size', type=float, default=0.02,
                        help='Quad size in meters (only used with --method quad)')
    parser.add_argument('--z_min', type=float, default=-float('inf'))
    parser.add_argument('--z_max', type=float, default=float('inf'))
    parser.add_argument('--x_min', type=float, default=-float('inf'))
    parser.add_argument('--x_max', type=float, default=float('inf'))
    parser.add_argument('--y_min', type=float, default=-float('inf'))
    parser.add_argument('--y_max', type=float, default=float('inf'))
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
    N = len(subset)
    print(f'  {N:,} selected')

    xyz = np.column_stack([subset['x'], subset['y'], subset['z']])
    rgb = sh_to_rgb(subset['f_dc_0'], subset['f_dc_1'], subset['f_dc_2'])

    if args.method == 'poisson':
        print(f'Poisson reconstruction (depth={args.depth})...')
        n_verts, n_faces = export_poisson(xyz, rgb, args.output, args.depth)
        print(f'  {n_verts:,} vertices, {n_faces:,} triangles')
    else:
        print(f'Quad mesh ({args.quad_size * 100:.1f}cm)...')
        # Build colored quads
        normals = np.column_stack([subset['nx'], subset['ny'], subset['nz']]).astype(np.float32)
        rgba = np.column_stack([(rgb * 255).astype(np.uint8), np.full(N, 255, dtype=np.uint8)])
        s = args.quad_size / 2
        verts = np.empty((N * 4, 3), dtype=np.float32)
        faces = np.empty((N * 2, 3), dtype=np.uint32)
        colors = np.empty((N * 4, 4), dtype=np.uint8)
        for i in range(N):
            nx, ny, nz = normals[i]
            if abs(nx) < 0.9:
                u = np.cross([nx, ny, nz], [1, 0, 0])
            else:
                u = np.cross([nx, ny, nz], [0, 1, 0])
            u_norm = np.linalg.norm(u)
            u = u / u_norm if u_norm > 1e-8 else np.array([1, 0, 0])
            v = np.cross([nx, ny, nz], u)
            v_norm = np.linalg.norm(v)
            v = v / v_norm if v_norm > 1e-8 else np.array([0, 1, 0])
            idx = i * 4
            x, y, z = xyz[i]
            verts[idx + 0] = [x + s * (-u[0] + v[0]), y + s * (-u[1] + v[1]), z + s * (-u[2] + v[2])]
            verts[idx + 1] = [x + s * (u[0] + v[0]), y + s * (u[1] + v[1]), z + s * (u[2] + v[2])]
            verts[idx + 2] = [x + s * (u[0] - v[0]), y + s * (u[1] - v[1]), z + s * (u[2] - v[2])]
            verts[idx + 3] = [x + s * (-u[0] - v[0]), y + s * (-u[1] - v[1]), z + s * (-u[2] - v[2])]
            fi = i * 2
            faces[fi + 0] = [idx, idx + 1, idx + 2]
            faces[fi + 1] = [idx, idx + 2, idx + 3]
            colors[idx: idx + 4] = rgba[i]
        import trimesh
        mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_colors=colors, process=False)
        mesh.export(args.output)
        n_verts, n_faces = len(verts), len(faces)

    size_mb = os.path.getsize(args.output) / 1024 / 1024
    print(f'  {size_mb:.1f} MB')
    print('  Blender: File → Import → glTF 2.0 (.glb) — colors auto-applied')
    print('Done.')


if __name__ == '__main__':
    main()