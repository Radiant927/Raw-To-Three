#!/usr/bin/env python3
"""Inspect COLMAP database: which image pairs matched, with how many inliers."""
import os, sys, sqlite3, math

db_path = sys.argv[1]
con = sqlite3.connect(db_path)
cur = con.cursor()
names = dict(cur.execute("SELECT image_id, name FROM images").fetchall())

# COLMAP pair_id: 0.5 * (i2-1) * (i2-2) + (i1-1), where i1 < i2 are 1-indexed image ids
rows = cur.execute(
    "SELECT pair_id, rows, config FROM two_view_geometries"
).fetchall()

pairs = []
for pair_id, n_matches, config in rows:
    if n_matches == 0:
        continue
    i2 = int((math.isqrt(8 * pair_id + 1) + 1) // 2) + 1
    i1 = pair_id - (i2 - 1) * (i2 - 2) // 2 + 1
    pairs.append((names.get(i1, f"#{i1}"), names.get(i2, f"#{i2}"), n_matches))

pairs.sort(key=lambda x: -x[2])
print(f"image ids: {len(names)}, matched pairs: {len(pairs)}")
for a, b, n in pairs:
    print(f"  {a} - {b}: {n} matches")
