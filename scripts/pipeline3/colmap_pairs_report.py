#!/usr/bin/env python3
"""Decode COLMAP pair_id and report which image pairs matched."""
import sqlite3, sys, math

db_path = sys.argv[1]
con = sqlite3.connect(db_path)
cur = con.cursor()
names = dict(cur.execute("SELECT image_id, name FROM images").fetchall())
print("image id->name:", names)

# matches table: pair_id, rows, cols, data
cur.execute("SELECT pair_id, rows FROM matches")
print("\nmatches table pairs (pair_id, count):")
rows = cur.fetchall()
for pid, n in rows:
    if n == 0:
        continue
    # decode COLMAP pair_id: pair_id = 0.5 * (image_id2 - 1) * (image_id2 - 2) + (image_id1 - 1)
    # image ids are 1-indexed in COLMAP, but here stored as given
    i2 = int((math.isqrt(8 * pid + 1) + 1) // 2) + 1
    i1 = pid - (i2 - 1) * (i2 - 2) // 2 + 1
    a = names.get(i1, f"#{i1}")
    b = names.get(i2, f"#{i2}")
    print(f"  {a:12s} - {b:12s} : {n} matches")

# also two_view_geometries for inliers
cur.execute("SELECT pair_id, rows, config FROM two_view_geometries")
print("\ntwo_view_geometries inliers:")
for pid, n, cfg in cur.fetchall():
    if n == 0:
        continue
    i2 = int((math.isqrt(8 * pid + 1) + 1) // 2) + 1
    i1 = pid - (i2 - 1) * (i2 - 2) // 2 + 1
    a = names.get(i1, f"#{i1}")
    b = names.get(i2, f"#{i2}")
    print(f"  {a:12s} - {b:12s} : {n} inliers")
