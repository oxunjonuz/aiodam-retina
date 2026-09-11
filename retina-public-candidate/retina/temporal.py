#!/usr/bin/env python3
"""retina_sensor.py — deterministic public-frame-only temporal sensor (t96).

Implements the owner-brief channels as testable code:
  global   : dH1 (16-bin colour histogram L1 delta), changed_area
  events   : colour-membership ON/OFF maps -> per-cluster move/appear/disappear
             events with greedy colour+proximity matching (scale-aware tolerance)
  ambient  : generic ambient mask — pixels that changed in >= AMBIENT_FRAC of the
             recent window are masked as ambient (HUD tick), no hardcoding
  pan      : coherent-motion detection (most changed pixels share one direction)
  window   : k-step temporal window; wall/no-op only declared when NO step in the
             window shows effective change (delayed-effect safe)

No game id, no seed, no private state: input is a list of 2-D int frames.
"""
import numpy as np

AMBIENT_FRAC = 0.6      # pixel changed in >=60% of window steps -> ambient
WINDOW = 2              # temporal window for wall/delayed decisions
PAN_AREA_FRAC = 0.30    # frame fraction changed before a pan is considered
PAN_DIR_FRAC = 0.50     # share of changed px voting one direction for a pan


def hist16(f):
    return np.bincount(np.asarray(f).flatten().astype(np.int64), minlength=16)[:16]


def global_channel(prev, cur):
    d = hist16(cur) - hist16(prev)
    diff = np.asarray(cur) != np.asarray(prev)
    return {
        "dH1": int(np.abs(d).sum()),
        "dH": [int(x) for x in d],
        "changed_area": int(diff.sum()),
        "appearing_colours": sorted(int(c) for c in np.where(d > 0)[0]),
        "disappearing_colours": sorted(int(c) for c in np.where(d < 0)[0]),
    }


def _clusters(mask, colour):
    """4-connected components of a boolean mask -> list of pixel sets."""
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    ys, xs = np.where(mask)
    coords = set(zip(ys.tolist(), xs.tolist()))
    for y0, x0 in coords:
        if seen[y0, x0]:
            continue
        stack = [(y0, x0)]
        seen[y0, x0] = True
        comp = []
        while stack:
            y, x = stack.pop()
            comp.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if (ny, nx) in coords and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        out.append({"colour": int(colour), "pixels": comp})
    return out


def _cluster_centroid_extent(comp):
    ys = [p[0] for p in comp["pixels"]]
    xs = [p[1] for p in comp["pixels"]]
    return ((sum(xs) / len(xs), sum(ys) / len(ys)),
            (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))


def _bbox(comp):
    ys = [p[0] for p in comp["pixels"]]
    xs = [p[1] for p in comp["pixels"]]
    return [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]


def event_channels(prev, cur):
    """Colour-membership ON/OFF event maps -> typed cluster events."""
    prev = np.asarray(prev)
    cur = np.asarray(cur)
    on_map = np.zeros_like(prev, dtype=bool)
    off_map = np.zeros_like(prev, dtype=bool)
    for c in range(16):
        on_map |= (cur == c) & (prev != c)
        off_map |= (prev == c) & (cur != c)
    on_clusters, off_clusters = [], []
    for c in range(16):
        on_clusters += _clusters((cur == c) & (prev != c), c)
        off_clusters += _clusters((prev == c) & (cur != c), c)
    events = []
    used_off = set()
    # greedy match ON to OFF clusters: same colour, centroid distance within a
    # scale-aware tolerance (1.5x the larger cluster's own extent, min 2px).
    # Rationale: an L-shaped partial overlap (object moving over background of
    # a different colour) splits the object into L-clusters whose centroids
    # separate by more than the object size; 1.5x extent covers that while a
    # distant distinct object of the same colour (>> extent apart) stays
    # unmatched. Known ambiguity: two same-colour objects appearing/disappearing
    # within ~1.5 extents of each other may be matched as one move.
    for onc in on_clusters:
        (ocx, ocy), (ow, oh) = _cluster_centroid_extent(onc)
        best, bestd = None, None
        for j, offc in enumerate(off_clusters):
            if j in used_off or offc["colour"] != onc["colour"]:
                continue
            (fcx, fcy), _ = _cluster_centroid_extent(offc)
            d = ((ocx - fcx) ** 2 + (ocy - fcy) ** 2) ** 0.5
            if bestd is None or d < bestd:
                best, bestd = j, d
        matched = False
        if best is not None:
            fc = off_clusters[best]
            (fcx, fcy), (fw, fh) = _cluster_centroid_extent(fc)
            tol = max(2.0, 1.5 * float(max(ow, oh, fw, fh)))
            if bestd <= tol:
                used_off.add(best)
                matched = True
                events.append({
                    "type": "move", "colour": onc["colour"],
                    "bbox": _bbox(onc),
                    "centroid": [round(ocx, 1), round(ocy, 1)],
                    "delta": [round(ocx - fcx, 1), round(ocy - fcy, 1)],
                    "area": len(onc["pixels"]),
                })
        if not matched:
            events.append({
                "type": "appear", "colour": onc["colour"],
                "bbox": _bbox(onc),
                "centroid": [round(ocx, 1), round(ocy, 1)],
                "delta": [0.0, 0.0], "area": len(onc["pixels"]),
            })
    for j, offc in enumerate(off_clusters):
        if j in used_off:
            continue
        (fcx, fcy), _ = _cluster_centroid_extent(offc)
        events.append({
            "type": "disappear", "colour": offc["colour"],
            "bbox": _bbox(offc),
            "centroid": [round(fcx, 1), round(fcy, 1)],
            "delta": [0.0, 0.0], "area": len(offc["pixels"]),
        })
    return {
        "on_px": int(on_map.sum()),
        "off_px": int(off_map.sum()),
        "events": sorted(events, key=lambda e: -e["area"]),
    }


def pan_detection(prev, cur):
    """Coherent background motion: most changed pixels share one direction.
    Multi-scale local search (shifts up to 3px) so a 3px camera pan votes."""
    prev = np.asarray(prev)
    cur = np.asarray(cur)
    diff = prev != cur
    n = int(diff.sum())
    if n < PAN_AREA_FRAC * diff.size:
        return {"is_pan": False, "changed": n}
    ys, xs = np.where(diff)
    sample = np.linspace(0, len(xs) - 1, min(400, len(xs))).astype(int)
    votes = {}
    for i in sample:
        y, x = int(ys[i]), int(xs[i])
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                if (dx, dy) == (0, 0):
                    continue
                yy, xx = y + dy, x + dx
                if (0 <= yy < prev.shape[0] and 0 <= xx < prev.shape[1]
                        and prev[yy, xx] == cur[y, x]
                        and prev[y, x] != cur[y, x]):
                    votes[(dx, dy)] = votes.get((dx, dy), 0) + 1
    if votes:
        best_dir, cnt = max(votes.items(), key=lambda kv: kv[1])
        if cnt >= PAN_DIR_FRAC * max(1, len(sample)):
            return {"is_pan": True, "changed": n, "direction": list(best_dir)}
    return {"is_pan": False, "changed": n}


def ambient_mask(frames, min_transitions=2):
    """Generic ambient mask: pixels changing in >= AMBIENT_FRAC of transitions.
    Degenerate guard: with fewer than min_transitions transitions every changed
    pixel trivially has fraction 1.0, which would mask the very change the
    sensor exists to see — so with too little history the mask is empty."""
    if len(frames) < 2:
        return np.zeros(np.asarray(frames[0]).shape, dtype=bool)
    changes = []
    for a, b in zip(frames[:-1], frames[1:]):
        changes.append(np.asarray(a) != np.asarray(b))
    if len(changes) < min_transitions:
        return np.zeros(np.asarray(frames[0]).shape, dtype=bool)
    stack = np.stack(changes)  # (T, H, W)
    frac = stack.mean(axis=0)
    return frac >= AMBIENT_FRAC


def effective_changed(prev, cur, mask):
    diff = np.asarray(prev) != np.asarray(cur)
    return int((diff & ~mask).sum())


def observe(frames):
    """Full packet over a frame list (>=1 frames). Returns per-step packets."""
    frames = [np.asarray(f) for f in frames]
    mask = ambient_mask(frames)
    packets = []
    for i in range(1, len(frames)):
        prev, cur = frames[i - 1], frames[i]
        g = global_channel(prev, cur)
        e = event_channels(prev, cur)
        pan = pan_detection(prev, cur)
        eff = effective_changed(prev, cur, mask)
        # wall/no-op decision over the trailing window, delayed-effect safe
        window_eff = [eff]
        j = i - 1
        while j >= 1 and len(window_eff) < WINDOW:
            window_eff.append(effective_changed(frames[j - 1], frames[j], mask))
            j -= 1
        packets.append({
            "step": i,
            "global": g,
            "events_head": e["events"][:6],
            "on_px": e["on_px"],
            "off_px": e["off_px"],
            "effective_changed": eff,
            "ambient_px": int(mask.sum()),
            "is_pan": pan["is_pan"],
            "pan_direction": pan.get("direction"),
            "window_effective": window_eff,
            "visible_effect": (
                "none" if max(window_eff) == 0
                else "pan" if pan["is_pan"]
                else "global" if g["changed_area"] > 40
                else "local"),
        })
    return packets
