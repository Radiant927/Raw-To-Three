#!/usr/bin/env python3
"""Check EXIF GPS/orientation data in images."""
import os, sys, glob
from PIL import Image
from PIL.ExifTags import TAGS

for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.jpg"))):
    try:
        exif = Image.open(f).getexif()
    except Exception:
        continue
    info = {}
    for tag_id, val in exif.items():
        name = TAGS.get(tag_id, tag_id)
        if name in ("GPSInfo", "Orientation", "Make", "Model", "DateTimeOriginal"):
            info[name] = val
    gps = ""
    if "GPSInfo" in info:
        g = info["GPSInfo"]
        try:
            lat = g.get(2)
            lon = g.get(4)
            gps = f" GPS lat={lat} lon={lon}"
        except Exception:
            gps = " GPS=yes"
    print(f"  {os.path.basename(f):12s} {info.get('Make','?')} {info.get('Model','?')} "
          f"orient={info.get('Orientation','-')} dt={str(info.get('DateTimeOriginal','-'))[:19]}{gps}")
