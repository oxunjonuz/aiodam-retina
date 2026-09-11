"""Original shared-perception implementation; see docs/PROVENANCE.md."""
from __future__ import annotations

import json

import numpy as np

from .retina_packet import (GRID, BBOX_CONVENTION, frame_to_hex_rows,
                           bbox_of, rasterize_bbox, modal_colour)

CONTRACT_LINE = (
    "[RETINA COORDINATE CONTRACT] origin=top-left; frame rows are printed "
    "top row first; row index is y, column index is x; a cell is "
    "frame[y][x]; ACTION6 payload {\"x\":X,\"y\":Y} addresses frame[Y][X]; "
    f"bbox=[y0,x0,y1,x1] inclusive ({BBOX_CONVENTION})."
)

GAME_TAIL = ('Return only JSON. For movement/interaction use {"action":N}; '
             'for a click use {"action":6,"x":X,"y":Y}.')


def _components(mask, min_size=1):
    """4-connected components of a boolean mask -> list of dicts with
    tight inclusive bboxes [y0,x0,y1,x1] (the canonical convention)."""
    lab = np.zeros_like(mask, dtype=np.int32)
    cur = 0
    out = []
    H, W = mask.shape
    for y in range(H):
        for x in range(W):
            if mask[y, x] and lab[y, x] == 0:
                cur += 1
                stack = [(y, x)]
                lab[y, x] = cur
                cells = []
                while stack:
                    cy, cx = stack.pop()
                    cells.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] \
                                and lab[ny, nx] == 0:
                            lab[ny, nx] = cur
                            stack.append((ny, nx))
                out.append({"cells": cells})
    out.sort(key=lambda c: -len(c["cells"]))
    return out


def observed_regions(delta_mask, max_regions=8):
    """Past-changed cells as compact tight bboxes, largest first.

    Each printed region rasterizes to a superset of the numeric component
    it summarizes; the count of covered cells is printed with it so Qwen
    can weigh it. Components smaller than min_size are aggregated into the
    total count and reported as one bbox of the union."""
    m = np.asarray(delta_mask) != 0
    if not m.any():
        return [], 0
    comps = [c for c in _components(m) if len(c["cells"]) >= 4]
    small = m.copy()
    for c in comps:
        for (y, x) in c["cells"]:
            small[y, x] = False
    regions = []
    for c in comps[:max_regions]:
        bb = bbox_of(_mask_of_cells(c["cells"]))
        regions.append({"bbox": bb, "cells": len(c["cells"])})
    n_small = int(small.sum())
    if n_small and len(regions) < max_regions:
        regions.append({"bbox": bbox_of(small), "cells": n_small,
                        "note": "scattered small changes (union bbox)"})
    elif n_small:
        regions[-1]["note"] = (f"+{n_small} scattered cells not itemized")
    return regions, int(m.sum())


def _mask_of_cells(cells):
    m = np.zeros((GRID, GRID), dtype=bool)
    for (y, x) in cells:
        m[y, x] = True
    return m


def serialize_observed(packet, available_actions, predictions=None,
                       click_memory=None) -> str:
    """Deterministic compact text FROM the canonical packet.

    packet       : src.retina_packet.build_packet output
    available_actions : engine-reported list at this step
    predictions  : optional connector dict — serialized under [PREDICTED]
    click_memory : optional {(x,y): {"trials":n,"no_op":k}} — serialized
                   under [OBSERVED] as verified no-op coordinates (only
                   confirmed-empty ones; the rest stay implicit)
    """
    g = packet["grid"]
    planes = packet["planes"]
    from .retina_packet import CH_DELTA
    delta = planes[CH_DELTA] > 0.5
    lines = [CONTRACT_LINE, "", "[OBSERVED FRAME] (hex, top row first):"]
    lines += frame_to_hex_rows(g)
    lines += ["", "[OBSERVED HISTORY]"]
    regions, total = observed_regions(delta)
    if total == 0:
        lines.append("changed_so_far=none")
    else:
        lines.append(f"changed_cells_so_far={total}")
        for r in regions[:8]:
            bb = r["bbox"]
            s = (f"changed_region bbox=[{bb[0]},{bb[1]},{bb[2]},{bb[3]}] "
                 f"cells={r['cells']}")
            if "note" in r:
                s += f" ({r['note']})"
            lines.append(s)
    eff = [(x, y) for y in range(GRID) for x in range(GRID)
           if planes[20, y, x] > 0.5]
    noop = [(x, y) for y in range(GRID) for x in range(GRID)
            if planes[21, y, x] > 0.5]
    lines.append("effective_clicks=" + (
        ",".join(f"(x={x},y={y})" for x, y in eff) if eff else "none"))
    lines.append("verified_noop_clicks=" + (
        ",".join(f"(x={x},y={y})" for x, y in noop) if noop else "none"))
    if click_memory:
        confirmed = sorted(
            (x, y) for (x, y), m in click_memory.items()
            if m["trials"] >= 2 and m["no_op"] == m["trials"])
        if confirmed:
            lines.append("confirmed_empty_coordinates=" + ",".join(
                f"(x={x},y={y})" for x, y in confirmed))
    lines.append(f"frame_hash={packet['frame_hash'][:16]}")
    hh = packet.get("history_hash")
    lines.append(f"history_hash={(hh[:16] if hh else 'none')}")
    lines += ["", "[CURRENT PUBLIC STATE]"]
    lines.append(f"available_actions={sorted(int(a) for a in available_actions)}")
    h16 = [int(x) for x in np.bincount(
        np.asarray(g).flatten().astype(np.int64), minlength=16)[:16]]
    lines.append(f"frame_hist16={h16}")
    lines.append(f"colours={sorted(int(c) for c in np.unique(np.asarray(g)))}")
    if predictions is not None:
        lines += ["", "[PREDICTED] (Grid-JEPA affordance layer; "
                  "probabilities, NOT observed facts; never a hard ban):"]
        lines.append(_serialize_predictions(predictions))
    lines += ["", GAME_TAIL]
    return "\n".join(lines)


def _serialize_predictions(pred: dict) -> str:
    """Compact deterministic prediction block. Observed/predicted field
    names never collide (predicted_* prefix)."""
    out = []
    for b in pred.get("blocked_regions", []):
        reg = b["region"]
        conf = b.get("confidence", 1.0)
        if b.get("reason") == "grid_edge":
            out.append(f"predicted_boundary=grid_edge confidence=1.0 "
                       "(observed rule: playable area is inside the border)")
        else:
            out.append(f"predicted_wall bbox=[{reg[0]},{reg[1]},{reg[2]},"
                       f"{reg[3]}] confidence={conf} "
                       "(probabilistic; not a ban)")
    for aid, a in sorted(pred.get("actions", {}).items(),
                         key=lambda kv: int(kv[0])):
        if a.get("hard_excluded"):
            continue
        out.append(f"predicted_action={aid} "
                   f"expected_effect={a['expected_effect']} "
                   f"no_op_probability={a.get('no_op_probability')} "
                   f"confidence={a.get('confidence')}")
        for reg in a.get("promising_regions", [])[:3]:
            out.append(f"  promising_region bbox=[{reg[0]},{reg[1]},"
                       f"{reg[2]},{reg[3]}] (ranked candidates)")
    if pred.get("recommended_candidates"):
        out.append("predicted_ranking=" +
                   ",".join(str(a) for a in pred["recommended_candidates"]) +
                   " (soft priority; every available action stays legal)")
    fam = pred.get("frame_familiarity") or {}
    if fam.get("status") in ("familiar", "unfamiliar"):
        out.append(f"predicted_familiarity={fam['status']} "
                   f"(mean_no_op={fam.get('mean_no_op_probability')})")
    return "\n".join(out)


# ---------------- parsers (for the parity round trip) ----------------

def parse_click_from_text(text: str, contract_present_text: str = ""):
    """Extract the first {"action":6,"x":X,"y":Y} decision from text and
    return (x, y). The parity test requires this to resolve to grid[y][x]
    — the same cell the numeric packet's click plane carries."""
    import re
    m = re.search(r'"action"\s*:\s*6\s*,\s*"x"\s*:\s*(\d+)\s*,\s*"y"\s*:\s*(\d+)',
                  text)
    if not m:
        m = re.search(r'"x"\s*=\s*(\d+)[, ]+"y"\s*=\s*(\d+)', text)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def bbox_from_text(text: str):
    """Parse 'bbox=[y0,x0,y1,x1]' — the CANONICAL order. Returns the tuple
    or None. (retina_sensor.py's [x0,y0,x1,y1] order is NOT accepted here:
    the serializer only ever prints canonical order, and the parity test
    proves the two orders differ on asymmetric data.)"""
    import re
    m = re.search(r"bbox=\[(\d+),(\d+),(\d+),(\d+)\]", text)
    if not m:
        return None
    return tuple(int(v) for v in m.groups())
