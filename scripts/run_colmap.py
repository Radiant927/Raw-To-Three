#!/usr/bin/env python3
"""COLMAP SfM reconstruction via pycolmap (no CLI needed).

Exit codes:
  0  success, enough cameras registered
  2  too few cameras registered (below --min_ratio or --min_cameras)
  3  reconstruction failed entirely (no cameras.bin)
"""
import argparse
import os
import sys
import glob
import pycolmap


def count_images(image_path):
    exts = ('*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG')
    files = []
    for e in exts:
        files.extend(glob.glob(os.path.join(image_path, e)))
        files.extend(glob.glob(os.path.join(image_path, '**', e), recursive=True))
    return len(set(files))


def main():
    parser = argparse.ArgumentParser(
        description='Run COLMAP SfM (feature extraction + matching + mapping)')
    parser.add_argument('--image_path', required=True, help='Path to input images')
    parser.add_argument('--output_path', required=True, help='Path for sparse output')
    parser.add_argument('--quality', default='high',
                        choices=['low', 'medium', 'high', 'extreme'],
                        help='Reconstruction quality (default: high)')
    parser.add_argument('--matcher', default='exhaustive',
                        choices=['exhaustive', 'sequential', 'spatial'],
                        help='Feature matching mode (default: exhaustive). '
                             'sequential is better for walk-around photo sequences; '
                             'spatial uses GPS if available.')
    parser.add_argument('--min_ratio', type=float, default=0.5,
                        help='Min ratio of registered cameras to input images (default: 0.5). '
                             'Below this, exit with code 2.')
    parser.add_argument('--min_cameras', type=int, default=20,
                        help='Absolute min number of registered cameras (default: 20).')
    parser.add_argument('--force', action='store_true',
                        help='Continue even if camera registration is below threshold.')
    args = parser.parse_args()

    os.makedirs(args.output_path, exist_ok=True)
    db_path = os.path.join(args.output_path, 'database.db')
    sparse_path = os.path.join(args.output_path, 'sparse')

    n_input = count_images(args.image_path)
    print(f'Input images: {n_input}')

    # Quality presets
    quality_configs = {
        'low':     {'max_num_features': 4000},
        'medium':  {'max_num_features': 8000},
        'high':    {'max_num_features': 12000},
        'extreme': {'max_num_features': 16000},
    }
    q = quality_configs[args.quality]

    # Step 1: Feature extraction
    print(f'[1/3] Extracting SIFT features (quality={args.quality}, matcher={args.matcher})...')
    extract_opts = pycolmap.FeatureExtractionOptions()
    extract_opts.sift.max_num_features = q['max_num_features']
    pycolmap.extract_features(
        database_path=db_path,
        image_path=args.image_path,
        extraction_options=extract_opts,
    )
    print('  Done.')

    # Step 2: Feature matching
    print(f'[2/3] Matching features ({args.matcher})...')
    match_opts = pycolmap.FeatureMatchingOptions()
    match_opts.max_num_matches = 32768

    if args.matcher == 'exhaustive':
        pycolmap.match_exhaustive(database_path=db_path, matching_options=match_opts)
    elif args.matcher == 'sequential':
        seq_opts = pycolmap.SequentialPairingOptions()
        seq_opts.overlap = 10
        seq_opts.quadratic_overlap = True
        pycolmap.match_sequential(
            database_path=db_path,
            matching_options=match_opts,
            pairing_options=seq_opts,
        )
    elif args.matcher == 'spatial':
        pycolmap.match_spatial(database_path=db_path, matching_options=match_opts)
    print('  Done.')

    # Step 3: Incremental mapping
    print('[3/3] Incremental mapping...')
    os.makedirs(sparse_path, exist_ok=True)

    mapper_opts = pycolmap.IncrementalPipelineOptions()
    mapper_opts.min_num_matches = 15

    reconstructions = pycolmap.incremental_mapping(
        database_path=db_path,
        image_path=args.image_path,
        output_path=sparse_path,
        options=mapper_opts,
    )

    sparse0 = os.path.join(sparse_path, '0')
    cameras_bin = os.path.join(sparse0, 'cameras.bin')
    images_bin = os.path.join(sparse0, 'images.bin')

    if not os.path.exists(cameras_bin):
        print('ERROR: Reconstruction failed — no cameras.bin produced')
        sys.exit(3)

    # Count registered cameras
    n_registered = 0
    if os.path.exists(images_bin):
        # images.bin format: each registered image is an entry
        # Use pycolmap to read if possible; else estimate from file size
        try:
            rec = pycolmap.Reconstruction(sparse0)
            n_registered = rec.num_reg_images()
        except Exception:
            n_registered = -1  # unknown

    ratio = n_registered / n_input if n_input > 0 else 0

    print(f'\n=== COLMAP result ===')
    print(f'  Input images:       {n_input}')
    print(f'  Registered cameras: {n_registered}')
    print(f'  Registration ratio: {ratio*100:.1f}%')
    print(f'  Output: {sparse0}')

    if n_registered < args.min_cameras or ratio < args.min_ratio:
        print()
        print('!' * 70)
        print('!! WARNING: LOW CAMERA REGISTRATION')
        print('!!')
        print(f'!!   Only {n_registered}/{n_input} cameras registered ({ratio*100:.1f}%)')
        print(f'!!   Threshold: min_cameras={args.min_cameras}, min_ratio={args.min_ratio*100:.0f}%')
        print('!!')
        print('!! This usually means:')
        print('!!   - Photos lack overlap between viewpoints (e.g. separated into')
        print('!!     subfolders with no bridging shots)')
        print('!!   - Matcher is wrong for how photos were taken')
        print('!!')
        print('!! Suggestions:')
        print('!!   - Add bridging photos between viewpoints')
        print('!!   - Re-run with --matcher sequential (for walk-around sequences)')
        print('!!   - Lower --min_ratio to force continuation')
        print('!!   - Re-run with --force to ignore this warning')
        print('!' * 70)
        if not args.force:
            print('\nAborting. Fix photo coverage or use --force / --matcher sequential to continue.')
            # Clean up partial 2DGS outputs that may get picked up later? No, leave COLMAP output.
            sys.exit(2)
        else:
            print('\n--force given, continuing despite low registration.')


if __name__ == '__main__':
    main()
