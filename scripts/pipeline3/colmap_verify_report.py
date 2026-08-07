#!/usr/bin/env python3
"""Dump per-pair two-view geometry verification results from a COLMAP db.

Decodes images, two_view_geometries (pair_id via Cantor pairing), config and
inlier count, so we can see exactly which pairs passed geometric verification
and with how many inliers.
"""
import argparse, sqlite3, numpy as np


def pair_decode(pair_id):
    k = int((np.sqrt(8 * pair_id + 1) - 1) / 2)
    b = pair_id - k * (k + 1) // 2
    a = k - b
    return a, b


def main():
    p = argparse.ArgumentParser()
    p.add_argument("db")
    args = p.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()

    img_rows = cur.execute("SELECT image_id, name FROM images").fetchall()
    name_by_id = {i: n for i, n in img_rows}
    print(f"images ({len(img_rows)}):")
    for i, n in sorted(img_rows):
        print(f"  {i}: {n}")

    print("\nverified pairs (two_view_geometries):")
    config_names = {0: "DEGENERATE", 1: "CALIBRATED", 2: "UNCALIBRATED",
                    3: "PLANAR/PANO", 4: "PLANAR_UNCAL", 5: "WATERMARK"}
    rows = cur.execute("SELECT pair_id, config, length(rows) FROM two_view_geometries").fetchall()
    if not rows:
        print("  (none) -- no pairs passed geometric verification")
    for pair_id, config, nbytes in rows:
        a, b = pair_decode(pair_id)
        na = name_by_id.get(a, a); nb = name_by_id.get(b, b)
        cn = config_names.get(config, config)
        # rows blob: serialized FeatureMatches -> each match is (u32,u32) = 8 bytes
        ninl = nbytes // 8
        print(f"  {na:12s} - {nb:12s}  config={cn:<14s} inliers={ninl}")

    # also keypoints / matches summary
    nk = cur.execute("SELECT count(*) FROM keypoints").fetchone()[0]
    nm = cur.execute("SELECT count(*) FROM matches").fetchone()[0]
    print(f"\nkeypoints: {nk}, raw match pairs: {nm}")
    con.close()


if __name__ == "__main__":
    main()
