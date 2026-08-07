#!/usr/bin/env python3
"""COLMAP for Kang statue: exhaustive matching with relaxed inlier thresholds."""
import argparse, os, sys
import pycolmap


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image_path", required=True)
    p.add_argument("--output_path", required=True)
    p.add_argument("--min_num_matches", type=int, default=8)
    p.add_argument("--max_features", type=int, default=16000)
    p.add_argument("--matcher", default="exhaustive", choices=["exhaustive", "sequential"])
    args = p.parse_args()

    os.makedirs(args.output_path, exist_ok=True)
    db_path = os.path.join(args.output_path, "database.db")
    sparse_path = os.path.join(args.output_path, "sparse")

    extract_opts = pycolmap.FeatureExtractionOptions()
    extract_opts.sift.max_num_features = args.max_features
    pycolmap.extract_features(database_path=db_path, image_path=args.image_path, extraction_options=extract_opts)
    print("[1/3] features extracted")

    match_opts = pycolmap.FeatureMatchingOptions()
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
    os.makedirs(sparse_path, exist_ok=True)
    reconstructions = pycolmap.incremental_mapping(
        database_path=db_path, image_path=args.image_path, output_path=sparse_path, options=mapper_opts
    )
    print("[3/3] mapping done, num models:", len(reconstructions))

    # Report all models
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
