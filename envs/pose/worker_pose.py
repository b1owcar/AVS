#!/usr/bin/env python3
"""Pose extract worker — runs inside env-pose (MediaPipe), not the main backend venv.

Usage:
  python worker_pose.py --request request.json --response response.json
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path


def _run(payload: dict) -> dict:
    import cv2
    import mediapipe as mp

    frame_paths = [Path(p) for p in payload["frame_paths"]]
    person_id = payload.get("person_id")
    min_conf = float(payload.get("min_detection_confidence", 0.5))
    coord = str(payload.get("coordinate_system") or "image_pixel")

    mp_pose = mp.solutions.pose
    results_frames = []
    persons_seen = 0

    with mp_pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=min_conf,
    ) as pose:
        for path in frame_paths:
            bgr = cv2.imread(str(path))
            if bgr is None:
                raise FileNotFoundError(f"cannot read image: {path}")
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            res = pose.process(rgb)
            if not res.pose_landmarks:
                results_frames.append(
                    {
                        "path": str(path),
                        "width": w,
                        "height": h,
                        "landmarks": [],
                        "person_count": 0,
                    }
                )
                continue

            persons_seen = max(persons_seen, 1)
            # MediaPipe Pose is single-person; person_id > 0 with no multi-person means empty
            if person_id is not None and int(person_id) > 0:
                results_frames.append(
                    {
                        "path": str(path),
                        "width": w,
                        "height": h,
                        "landmarks": [],
                        "person_count": 1,
                        "note": f"person_id={person_id} not available (single-person Pose)",
                    }
                )
                continue

            landmarks = []
            for i, lm in enumerate(res.pose_landmarks.landmark):
                if coord == "normalized":
                    landmarks.append(
                        {
                            "id": i,
                            "x": float(lm.x),
                            "y": float(lm.y),
                            "z": float(lm.z),
                            "visibility": float(getattr(lm, "visibility", 0.0)),
                        }
                    )
                else:
                    landmarks.append(
                        {
                            "id": i,
                            "x": float(lm.x * w),
                            "y": float(lm.y * h),
                            "z": float(lm.z),
                            "visibility": float(getattr(lm, "visibility", 0.0)),
                        }
                    )
            results_frames.append(
                {
                    "path": str(path),
                    "width": w,
                    "height": h,
                    "landmarks": landmarks,
                    "person_count": 1,
                }
            )

    return {
        "ok": True,
        "is_simulation": False,
        "frames": results_frames,
        "persons_detected": persons_seen,
        "output_files": [],
        "message": f"pose extract on {len(results_frames)} frame(s); persons_detected={persons_seen}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args()

    req_path = Path(args.request)
    resp_path = Path(args.response)
    payload = json.loads(req_path.read_text(encoding="utf-8"))

    try:
        resp = _run(payload)
        resp_path.write_text(json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    except Exception as exc:  # noqa: BLE001
        resp = {
            "ok": False,
            "is_simulation": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "message": f"pose worker failed: {exc}",
        }
        resp_path.write_text(json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
        print(resp["message"], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
