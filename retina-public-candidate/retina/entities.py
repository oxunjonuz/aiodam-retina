"""Verbatim entity functions from the preserved server-run semantic module."""
import hashlib
import numpy as np

def entities(frame) -> list:
    """ALL 4-connected components of the current frame (deterministic,
    scan order = row-major). Returns dicts with colour, bbox, area,
    centroid, mask_sha16 (lossless mask identity) and exact pixel list."""
    a = np.asarray(frame).astype(int)
    h, w = a.shape
    seen = np.zeros_like(a, dtype=bool)
    out = []
    for yy in range(h):
        for xx in range(w):
            if seen[yy, xx]:
                continue
            col = int(a[yy, xx])
            stack = [(yy, xx)]
            seen[yy, xx] = True
            pix = []
            while stack:
                y, x = stack.pop()
                pix.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] \
                            and int(a[ny, nx]) == col:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            ys = [p[0] for p in pix]
            xs = [p[1] for p in pix]
            area = len(pix)
            bbox = (min(xs), min(ys), max(xs), max(ys))
            cy = sum(ys) / area
            cx = sum(xs) / area
            mask = np.zeros_like(a, dtype=np.int8)
            for y, x in pix:
                mask[y, x] = 1
            mh = hashlib.sha256(
                mask.tobytes() + b"|mask").hexdigest()[:16]
            out.append({"colour": col, "bbox": list(bbox), "area": area,
                        "centroid": [round(cx, 1), round(cy, 1)],
                        "mask_sha16": mh,
                        "pix": sorted(pix)})
    return out



def entity_line(frame) -> str:
    """Compact deterministic digest of ALL entities of the current frame.
    Small (area<=2) entities ultra-compact; larger with bbox+area+centroid
    + mask sha. Sorted by (colour, bbox) for determinism."""
    ents = entities(frame)
    parts = []
    for e in sorted(ents, key=lambda e: (e["colour"], e["bbox"])):
        if e["area"] <= 2:
            px = ",".join(f"{x},{y}" for y, x in e["pix"])
            parts.append(f"e:c{e['colour']}@{px}")
        else:
            x0, y0, x1, y1 = e["bbox"]
            parts.append(
                f"e:c{e['colour']}@{x0},{y0},{x1},{y1} a{e['area']} "
                f"ctr[{e['centroid'][0]},{e['centroid'][1]}] "
                f"m={e['mask_sha16']}")
    return f"entities={len(ents)}; " + "; ".join(parts)



def verify_entities(frame, line: str) -> list:
    """V3: recompute the entity digest from the frame bytes and compare
    with the rendered line."""
    want = entity_line(frame)
    return [] if want == line else ["entity line mismatch"]

