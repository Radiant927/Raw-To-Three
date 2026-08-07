#!/usr/bin/env python3
"""Insert self.depth storage into 2d-gs scene/cameras.py (idempotent)."""
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "scene/cameras.py"
s = open(path, "r", encoding="utf-8").read()

if "self.depth" in s:
    print("already patched")
    sys.exit(0)

anchor = "            self.gt_alpha_mask = None\n        \n        self.zfar = 100.0"
insert = (
    "            self.gt_alpha_mask = None\n"
    "\n"
    "        if depth is not None:\n"
    "            import torch.nn.functional as F\n"
    "            depth_tensor = torch.from_numpy(depth).unsqueeze(0).unsqueeze(0)  # (1,1,H,W)\n"
    "            depth_tensor = F.interpolate(depth_tensor, size=(self.image_height, self.image_width), mode='bilinear', align_corners=False)\n"
    "            self.depth = depth_tensor.squeeze(0)  # (1, H, W)\n"
    "        else:\n"
    "            self.depth = None\n"
    "        \n"
    "        self.zfar = 100.0"
)

if anchor not in s:
    print("ERROR: anchor not found")
    sys.exit(1)

s = s.replace(anchor, insert, 1)
open(path, "w", encoding="utf-8").write(s)
print("depth storage inserted OK")
