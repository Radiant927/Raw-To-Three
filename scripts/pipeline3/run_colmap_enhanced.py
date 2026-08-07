#!/usr/bin/env python3
"""Enhanced COLMAP for dark/low-texture subjects:
- optional gamma brightening of input images into a temp dir
- lowered SIFT contrast_threshold (extract more features on low-texture areas)
- tunable matcher min inliers + mapper min matches, optional forced init pair
"""
import argparse, os, sys, glob, shutil
import numpy as np, cv2
import pycolmap


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image_path", required=True)
    p.add_argument("--output_path", required=True)
    p.add_argument("--gamma", type=float, default=1.0, help="1.0 = no change; >1 brighten shadows")
    p.add_argument("--contrast_threshold", type=float, default=0.04, help="SIFT contrast threshold (0.04 default)")
    p.add_argument("--max_features", type=int, default=20000)
    p.add_argument("--min_num_inliers", type=int, default=15, help="matcher two-view min inliers")
    p.add_argument("--min_num_matches", type=int, default=12, help="mapper registration min matches")
    p.add_argument("--init_pair", default=None, help="'a,b' 1-based image indices to force as initial pair")
    p.add_argument("--matcher", default="exhaustive", choices=["exhaustive", "sequential"])
    args = p.parse_args()

    os.makedirs(args.output_path, exist_ok=True)

    # Optional gamma enhance into work images dir
    work_images = args.image_path
    if args.gamma != 1.0:
        work_images = os.path.join(args.output_path, "images_enh")
        os.makedirs(work_images, exist_ok=True)
        for f in sorted(glob.glob(os.path.join(args.image_path, "*.jpg"))) + \
                 sorted(glob.glob(os.path.join(args.image_path, "*.png"))):
            img = cv2.imread(f)
            inv_gamma = 1.0 / args.gamma
            lut = np.array([(i / 255.0) ** inv_gamma * 255 for i in range(256)], dtype=np.uint8)
            out = cv2.LUT(img, lut)
            dst = os.path.join(work_images, os.path.basename(f))
            cv2.imwrite(dst, out)
        print(f"gamma {args.gamma} applied -> {work_images} ({len(glob.glob(os.path.join(work_images,'*')))} files)")

    db_path = os.path.join(args.output_path, "database.db")
    sparse_path = os.path.join(args.output_path, "sparse")
    os.makedirs(sparse_path, exist_ok=True)

    extract_opts = pycolmap.FeatureExtractionOptions()
    extract_opts.sift.max_num_features = args.max_features
    try:
        extract_opts.sift.peak_threshold = args.contrast_threshold
        print(f"peak_threshold(contrast)={args.contrast_threshold}")
    except Exception as e:
        print("peak_threshold not settable:", e)
    try:
        extract_opts.sift.edge_threshold = 20.0
    except Exception:
        pass
    pycolmap.extract_features(database_path=db_path, image_path=work_images, extraction_options=extract_opts)
    print("[1/3] features extracted")

    match_opts = pycolmap.FeatureMatchingOptions()
    try:
        match_opts.sift.min_num_inliers = args.min_num_inliers
        print(f"matcher min_num_inliers={args.min_num_inliers}")
    except Exception as e:
        print("matcher min_num_inliers not settable:", e)
    match_opts.max_num_matches = 32768
    if args.matcher == "exhaustive":
        pycolmap.match_exhaustive(database_path=db_path, matching_options=match_opts)
    else:
        seq_opts = pycolmap.SequentialPairingOptions()
        seq_opts.overlap = 10
        seq_opts.quadratic_overlap = True
        pycolmap.match_sequential(database_path=db_path, matching_options=match_opts, pairing_options=seq_opts)
    print("[2/3] features matched")

    mapper_opts = pycolmap.IncrementalPipelineOptions()
    mapper_opts.min_num_matches = args.min_num_matches
    if args.init_pair:
        a, b = (int(x) for x in args.init_pair.split(","))
        mapper_opts.init_image_id1 = a
        mapper_opts.init_image_id2 = b
        print(f"forced init pair: image ids {a}, {b}")
    reconstructions = pycolmap.incremental_mapping(
        database_path=db_path, image_path=work_images, output_path=sparse_path, options=mapper_opts
    )
    print("[3/3] mapping done, num models:", len(reconstructions))

    for d in sorted(os.listdir(sparse_path)):
        p0 = os.path.join(sparse_path, d)
        if not os.path.isdir(p0):
            continue
        try:
            r = pycolmap.Reconstruction(p0)
            names = sorted(x.name for x in r.images.values())
            print(f"  model {d}: {r.num_reg_images()} images, {r.num_points3D()} points")
            print(f"    {names}")
        except Exception as e:
            print(f"  model {d}: ERR {e}")


if __name__ == "__main__":
    main()
