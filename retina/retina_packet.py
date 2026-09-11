"""Original shared-perception implementation; see docs/PROVENANCE.md."""
from __future__ import annotations

import hashlib
import json

import numpy as np

GRID = 64
N_COLOURS = 16
SCHEMA = "arc3-retina-packet-v1"

# channel indices
CH_COLOUR = 0        # 0..15
CH_X = 16
CH_Y = 17
CH_VALID = 18
CH_DELTA = 19
CH_EFF_CLICK = 20
CH_NOOP_CLICK = 21
N_CHANNELS = 22
# the six planes the Grid-JEPA side branch consumes (X, Y, valid, delta,
# effective click, verified no-op click)
SIDE_CHANNELS = (CH_X, CH_Y, CH_VALID, CH_DELTA, CH_EFF_CLICK, CH_NOOP_CLICK)
N_SIDE = len(SIDE_CHANNELS)

BBOX_CONVENTION = "[y0,x0,y1,x1] inclusive"

CONTRACT_TEXT = (
    "[RETINA COORDINATE CONTRACT] origin=top-left; grid is grid[y][x] "
    "(row y, column x); ACTION6 payload is x,y and addresses grid[y][x]; "
    "x_plane[y][x]=x/63; y_plane[y][x]=y/63; "
    "bbox=[y0,x0,y1,x1] inclusive (cell (x,y) is inside iff "
    "y0<=y<=y1 and x0<=x<=x1)."
)


def _as_grid(frame) -> np.ndarray:
    a = np.asarray(frame)
    if a.shape != (GRID, GRID):
        raise ValueError(f"frame shape {a.shape} != {(GRID, GRID)}")
    a = a.astype(np.int16)
    if a.min() < 0 or a.max() > 15:
        raise ValueError(f"colour values out of 0..15: "
                         f"{a.min()}..{a.max()}")
    return a


def sha_grid_bytes(frame) -> str:
    """frame_hash: sha256 of int16 row-major bytes.

    Equals frame_t_sha256 of datasets/transitions_*.jsonl and
    datasets/affordance_labels_v2.jsonl (same convention, verified)."""
    a = np.ascontiguousarray(_as_grid(frame))
    return hashlib.sha256(a.tobytes()).hexdigest()


def initial_history_hash(frame0) -> str:
    """h0: the chain starts from the episode's first public frame."""
    return sha_grid_bytes(frame0)


def history_chain_step(prev_hash_hex: str, step, action_id, x, y,
                       effective: bool, frame_after) -> str:
    """h_{j+1} = sha256(h_j || canonical_json(record_j)).

    The record carries the executed public action, its verified outcome
    and the sha of the frame it produced — the ordered public transition
    record of TZ par. 4."""
    rec = {
        "step": int(step),
        "action": int(action_id),
        "x": None if x is None else int(x),
        "y": None if y is None else int(y),
        "effective": bool(effective),
        "frame_after_sha256": sha_grid_bytes(frame_after),
    }
    h = hashlib.sha256()
    h.update(prev_hash_hex.encode("ascii"))
    h.update(json.dumps(rec, sort_keys=True).encode("ascii"))
    return h.hexdigest()


def _check_click(x, y):
    x, y = int(x), int(y)
    if not (0 <= x < GRID and 0 <= y < GRID):
        raise ValueError(f"click ({x},{y}) outside the 64x64 grid — "
                         "the canonical packet refuses illegal coordinates "
                         "(no silent ignoring)")
    return x, y


def build_packet(frame, delta_mask=None, effective_clicks=None,
                 noop_clicks=None, history_hash=None) -> dict:
    """Build the canonical packet from OBSERVED evidence only.

    frame             : 64x64 int grid, colours 0..15 (the public frame)
    delta_mask        : (64,64) bool/0-1 — cells changed at any PAST step
    effective_clicks  : [(x, y), ...] EXECUTED ACTION6 with observed effect
    noop_clicks       : [(x, y), ...] EXECUTED ACTION6 with observed no-op
    history_hash      : the chain hash h_k over steps 0..k-1 (None at step 0
                        is allowed and serialized as 'none')

    Returns dict with: grid (int16), planes (22,64,64 float32),
    frame_hash, history_hash, conventions.
    """
    g = _as_grid(frame)
    planes = np.zeros((N_CHANNELS, GRID, GRID), dtype=np.float32)
    for c in range(N_COLOURS):
        planes[c] = (g == c).astype(np.float32)
    ys, xs = np.mgrid[0:GRID, 0:GRID]
    planes[CH_X] = (xs / 63.0).astype(np.float32)
    planes[CH_Y] = (ys / 63.0).astype(np.float32)
    planes[CH_VALID] = 1.0
    if delta_mask is not None:
        dm = np.asarray(delta_mask)
        if dm.shape != (GRID, GRID):
            raise ValueError(f"delta_mask shape {dm.shape}")
        planes[CH_DELTA] = (dm != 0).astype(np.float32)
    for (x, y) in (effective_clicks or []):
        x, y = _check_click(x, y)
        planes[CH_EFF_CLICK, y, x] = 1.0
    for (x, y) in (noop_clicks or []):
        x, y = _check_click(x, y)
        planes[CH_NOOP_CLICK, y, x] = 1.0
    return {
        "schema": SCHEMA,
        "grid": g,
        "planes": planes,
        "frame_hash": sha_grid_bytes(g),
        "history_hash": history_hash,
        "conventions": {
            "origin": "top-left",
            "indexing": "tensor[y,x]",
            "action6_coordinates": "x,y",
            "bbox": BBOX_CONVENTION,
            "frame_hash": "sha256(int16 row-major grid bytes)",
            "history_hash": "chain over ordered public transition records",
        },
    }


def packet_from_context(frame, context: dict) -> dict:
    """Build the packet for one row from its precomputed retina context
    (datasets/retina_contexts_v2.jsonl): delta bits + click lists +
    chain hash. The context file is a CACHE; the parity verifier
    recomputes contexts from the raw public transitions and compares
    byte-for-byte."""
    delta = unpack_delta(context["delta_hex"])
    return build_packet(
        frame,
        delta_mask=delta,
        effective_clicks=[tuple(c) for c in context.get("effective_clicks", [])],
        noop_clicks=[tuple(c) for c in context.get("noop_clicks", [])],
        history_hash=context.get("chain_hash"),
    )


def packet_to_model_input(packet: dict):
    """Grid-JEPA numeric-branch input derived from the SAME packet.

    Returns (grid_int64 (64,64), side_planes float32 (6,64,64)).
    The colour path consumes the grid through the trained 16-colour
    embedding — mathematically identical to consuming the packet's one-hot
    planes (one-hot @ W == W[grid]; parity-tested). The side branch
    consumes the packet's X/Y/valid/delta/click planes verbatim — no
    rescaling, the packet is the truth."""
    grid = packet["grid"].astype(np.int64)
    side = np.ascontiguousarray(packet["planes"][list(SIDE_CHANNELS)])
    return grid, side


def side_planes_from_parts(delta_mask=None, effective_clicks=None,
                           noop_clicks=None) -> np.ndarray:
    """The (6,64,64) side stack without building the full packet
    (trainer fast path; X/Y/valid are grid-independent constants)."""
    side = np.zeros((N_SIDE, GRID, GRID), dtype=np.float32)
    ys, xs = np.mgrid[0:GRID, 0:GRID]
    side[0] = (xs / 63.0).astype(np.float32)
    side[1] = (ys / 63.0).astype(np.float32)
    side[2] = 1.0
    if delta_mask is not None:
        side[3] = (np.asarray(delta_mask) != 0).astype(np.float32)
    for (x, y) in (effective_clicks or []):
        x, y = _check_click(x, y)
        side[4, y, x] = 1.0
    for (x, y) in (noop_clicks or []):
        x, y = _check_click(x, y)
        side[5, y, x] = 1.0
    return side


def pack_delta(mask) -> str:
    """(64,64) mask -> 1024 hex chars (np.packbits, bitorder='big',
    row-major y*64+x bit order). Deterministic; parity-tested round trip."""
    bits = (np.asarray(mask) != 0).astype(np.uint8).flatten()
    return np.packbits(bits, bitorder="big").tobytes().hex()


def unpack_delta(hexstr: str) -> np.ndarray:
    raw = bytes.fromhex(hexstr)
    bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8), bitorder="big")
    return bits[:GRID * GRID].reshape(GRID, GRID).astype(bool)


def bbox_of(mask) -> list:
    """Tight inclusive bbox [y0,x0,y1,x1] of a boolean mask (None if empty)."""
    m = np.asarray(mask) != 0
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        return None
    return [int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())]


def rasterize_bbox(bbox) -> np.ndarray:
    """Boolean mask of the inclusive bbox [y0,x0,y1,x1]. The parity test
    requires: rasterize(bbox_of(mask)) ⊇ mask and bbox is tight."""
    y0, x0, y1, x1 = [int(v) for v in bbox]
    m = np.zeros((GRID, GRID), dtype=bool)
    m[y0:y1 + 1, x0:x1 + 1] = True
    return m


def frame_to_hex_rows(frame) -> list:
    """64 hex rows, top row first — the exact t178 live layout bytes
    (frame_to_hex_rows of reference_qwen/t178_universal_agent.py)."""
    g = _as_grid(frame)
    return ["".join("%x" % int(v) for v in row) for row in g]


def hex_rows_to_frame(rows) -> np.ndarray:
    """Lossless inverse of frame_to_hex_rows (round-trip parity-tested)."""
    if len(rows) != GRID or any(len(r) != GRID for r in rows):
        raise ValueError("bad hex rows")
    return np.array([[int(ch, 16) for ch in row] for row in rows],
                    dtype=np.int16)


def modal_colour(frame) -> int:
    g = _as_grid(frame)
    return int(np.bincount(g.ravel(), minlength=N_COLOURS).argmax())
