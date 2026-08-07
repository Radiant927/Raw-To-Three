#!/usr/bin/env python3
"""Report per-image SIFT feature counts and matched pairs from COLMAP db."""
import sqlite3, sys

db_path = sys.argv[1]
con = sqlite3.connect(db_path)
cur = con.cursor()

tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("tables:", tables)

cur.execute("SELECT image_id, rows, cols FROM keypoints")
feats = {}
for iid, rows, cols in cur.fetchall():
    feats[iid] = rows

cur.execute("SELECT image_id, name FROM images")
for iid, name in cur.fetchall():
    print(f"  img id={iid:2d} {name:12s} features={feats.get(iid, 0)}")
