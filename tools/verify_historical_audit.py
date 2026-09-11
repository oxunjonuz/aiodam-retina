#!/usr/bin/env python3
"""Independent verifier for raw-frame/global-channel claims in the audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def expected_global(prev: np.ndarray, cur: np.ndarray) -> dict:
    hp = np.bincount(prev.ravel().astype(np.int64), minlength=16)[:16]
    hc = np.bincount(cur.ravel().astype(np.int64), minlength=16)[:16]
    delta = hc - hp
    changed = int(np.count_nonzero(prev != cur))
    return {
        "dH": [int(x) for x in delta],
        "dH1": int(np.abs(delta).sum()),
        "changed_area": changed,
        "on_px": changed,
        "off_px": changed,
    }


def components(mask: np.ndarray, x_offset: int, y_offset: int) -> list[dict]:
    seen = np.zeros_like(mask, dtype=bool)
    found = []
    height, width = mask.shape
    for y0, x0 in zip(*np.where(mask)):
        if seen[y0, x0]:
            continue
        stack = [(int(y0), int(x0))]
        seen[y0, x0] = True
        pixels = []
        while stack:
            y, x = stack.pop()
            pixels.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if (0 <= ny < height and 0 <= nx < width
                        and mask[ny, nx] and not seen[ny, nx]):
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        ys = np.asarray([p[0] + y_offset for p in pixels])
        xs = np.asarray([p[1] + x_offset for p in pixels])
        found.append({
            "area": len(pixels),
            "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "centroid": [round(float(xs.mean()), 1), round(float(ys.mean()), 1)],
        })
    return found


def validate_packet(packet: dict, prev: np.ndarray, cur: np.ndarray) -> list[str]:
    errors = []
    exp = expected_global(prev, cur)
    for key in ("dH", "dH1", "changed_area"):
        if packet["global"][key] != exp[key]:
            errors.append(f"global.{key}")
    for key in ("on_px", "off_px"):
        if packet[key] != exp[key]:
            errors.append(key)
    for index, event in enumerate(packet["events_head"]):
        x0, y0, x1, y1 = event["bbox"]
        if not (0 <= x0 <= x1 < 64 and 0 <= y0 <= y1 < 64):
            errors.append(f"events_head[{index}].bbox")
            continue
        cx, cy = event["centroid"]
        if not (x0 <= cx <= x1 and y0 <= cy <= y1):
            errors.append(f"events_head[{index}].centroid")
        colour = event["colour"]
        region_prev = prev[y0:y1 + 1, x0:x1 + 1]
        region_cur = cur[y0:y1 + 1, x0:x1 + 1]
        if event["type"] in ("move", "appear"):
            evidence = (region_cur == colour) & (region_prev != colour)
        else:
            evidence = (region_prev == colour) & (region_cur != colour)
        candidates = [c for c in components(evidence, x0, y0)
                      if c["bbox"] == event["bbox"] and c["area"] == event["area"]]
        if not candidates:
            errors.append(f"events_head[{index}].component")
        elif event["centroid"] not in [c["centroid"] for c in candidates]:
            errors.append(f"events_head[{index}].centroid_exact")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    root = args.eval_root.resolve()
    report_path = root / "output" / "audit_report.json"
    manifest_path = root / "output" / "artifact_manifest.json"
    report = json.loads(report_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    failures = []

    if sha256_file(report_path) != manifest["report"]["sha256"]:
        failures.append("report hash")
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        if not path.is_file() or path.stat().st_size != artifact["bytes"] or sha256_file(path) != artifact["sha256"]:
            failures.append(f"artifact integrity: {artifact['path']}")

    tamper_rejections = 0
    for case in report["cases"]:
        case_dir = root / "output" / case["case"]
        prev = np.load(case_dir / "previous.npy", allow_pickle=False)
        cur = np.load(case_dir / "current.npy", allow_pickle=False)
        packet = json.loads((case_dir / "retina_packet.json").read_text())
        tampered = json.loads((case_dir / "retina_packet_tampered.json").read_text())
        errors = validate_packet(packet, prev, cur)
        if errors:
            failures.append(f"{case['case']} canonical: {','.join(errors)}")
        tampered_errors = validate_packet(tampered, prev, cur)
        if tampered_errors:
            tamper_rejections += 1
        else:
            failures.append(f"{case['case']} tamper accepted")

    if tamper_rejections != len(report["cases"]):
        failures.append("tamper rejection count")
    if report["sources"]["frozen_sensor"]["sha256"] != report["sources"]["active_sensor_read_only"]["sha256"]:
        failures.append("frozen sensor differs from pinned active source")

    verdict = {
        "verdict": "PASS" if not failures else "FAIL",
        "canonical_cases_verified": len(report["cases"]),
        "tamper_cases_rejected": tamper_rejections,
        "failures": failures,
    }
    if args.result:
        args.result.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n")
    print(json.dumps(verdict, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
