#!/usr/bin/env python3
"""Report matched image pairs from a COLMAP database using pycolmap API."""
import os, sys
import pycolmap

db_path = sys.argv[1]
db = pycolmap.Database(db_path)
images = db.read_all_images()
name_of = {img.image_id: img.name for img in images}

print(f"images in db: {len(name_of)}")
for iid in sorted(name_of):
    print(f"  id={iid}: {name_of[iid]}")

geos = db.read_two_view_geometries()
out = []
for pair_id, geo in geos.items():
    if geo is None or geo.num_inliers == 0:
        continue
    # pycolmap pair_id: high 32 bits = larger id, low 32 bits = smaller id? try bit ops
    i2 = pair_id >> 32
    i1 = pair_id & 0xFFFFFFFF
    if i2 not in name_of or i1 not in name_of:
        # try swapping
        i2, i1 = i1, i2
    out.append((name_of.get(i1, f"#{i1}"), name_of.get(i2, f"#{i2}"), geo.num_inliers))

out.sort(key=lambda x: -x[2])
print(f"\nmatched pairs: {len(out)}")
for a, b, n in out:
    print(f"  {a} - {b}: {n} inliers")
