#!/usr/bin/env python3
"""Patch cameras.bin: SIMPLE_RADIAL (model_id=2, 4 params) → SIMPLE_PINHOLE (model_id=0, 3 params).

Uses cam_updates.json from undistort_images.py to update focal length and principal point.
After undistortion, k1 is zero (images are undistorted), so SIMPLE_PINHOLE is correct.

cameras.bin binary format:
  Header: num_cameras (uint64)
  Per camera:
    cam_id    (uint32)
    model_id  (uint32)   ← change from 2 → 0
    width     (uint64)
    height    (uint64)
    params    (N × float64) ← change from [f, cx, cy, k1] to [f_new, cx_new, cy_new]
"""
import argparse, json, os, struct


MODEL_PARAMS = {0: 3, 1: 4, 2: 4, 3: 5, 4: 8, 5: 8, 6: 12, 7: 5, 8: 4, 9: 5, 10: 12}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Input cameras.bin path")
    p.add_argument("--output", required=True, help="Output cameras.bin path")
    p.add_argument("--cam_updates", required=True, help="cam_updates.json from undistort_images.py")
    args = p.parse_args()

    with open(args.cam_updates) as f:
        updates = json.load(f)

    with open(args.input, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        cameras = {}
        for _ in range(n):
            cam_id = struct.unpack("<I", f.read(4))[0]
            model_id = struct.unpack("<I", f.read(4))[0]
            w = struct.unpack("<Q", f.read(8))[0]
            h = struct.unpack("<Q", f.read(8))[0]
            np_ = MODEL_PARAMS.get(model_id, 4)
            params = struct.unpack(f"<{np_}d", f.read(8 * np_))
            cameras[cam_id] = (model_id, w, h, params)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(struct.pack("<Q", len(cameras)))
        for cam_id in sorted(cameras.keys()):
            model_id, w, h, params = cameras[cam_id]
            if str(cam_id) in updates and model_id == 2:  # SIMPLE_RADIAL → SIMPLE_PINHOLE
                u = updates[str(cam_id)]
                avg_f = (u["fx"] + u["fy"]) / 2.0
                new_model_id = 0  # SIMPLE_PINHOLE
                new_params = (avg_f, u["cx"], u["cy"])
                print(f"  Cam {cam_id}: SIMPLE_RADIAL → SIMPLE_PINHOLE f={avg_f:.1f} cx={u['cx']:.1f} cy={u['cy']:.1f}")
            else:
                new_model_id = model_id
                new_params = params[:MODEL_PARAMS.get(new_model_id, len(params))]
            f.write(struct.pack("<IIQQ", cam_id, new_model_id, w, h))
            for pv in new_params:
                f.write(struct.pack("<d", pv))

    print(f"Written {len(cameras)} cameras to {args.output}")


if __name__ == "__main__":
    main()
