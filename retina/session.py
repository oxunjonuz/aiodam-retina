"""New release glue, not the implementation measured in the 2026-08-27 audit.

Keeps all observations. Temporal association is not a causal proof.
"""
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

from .event_guard import _guard_events
from .entities import entity_line, verify_entities
from .retina_packet import build_packet, frame_to_hex_rows
from .spatial_legacy import center_patch
from .temporal import _bbox, _clusters, event_channels, hist16, observe


def _grid(frame):
    a = np.asarray(frame)
    if a.shape != (64, 64) or not np.issubdtype(a.dtype, np.integer):
        raise ValueError("expected a 64x64 integer grid")
    if a.min() < 0 or a.max() > 15:
        raise ValueError("expected colour indices 0..15")
    return a.astype("<i2", copy=True)


def _hash(frame):
    return hashlib.sha256(frame.astype("<i2").tobytes(order="C")).hexdigest()


def _actions(actions):
    values = list(actions)
    if any(type(a) is not int or a < 0 for a in values):
        raise ValueError("available actions must be nonnegative integer IDs")
    return values


def _decision(action, available):
    if not isinstance(action, dict) or type(action.get("action")) is not int:
        raise ValueError("action must contain an integer action ID")
    aid = action["action"]
    if aid not in available:
        raise ValueError("action was not available in the preceding state")
    allowed = {"action", "x", "y"} if aid == 6 else {"action"}
    if set(action) != allowed:
        raise ValueError("unexpected or missing action fields")
    if aid == 6 and any(type(action[k]) is not int or not 0 <= action[k] < 64 for k in ("x", "y")):
        raise ValueError("click coordinates must be integers in 0..63")
    return copy.deepcopy(action)


class RetinaSession:
    """One game's complete observation journal; instantiate separately per game.

    append() must be called AFTER the external environment executes the action.
    This package cannot verify that caller-supplied frames came from a real engine.
    All records are delivered by to_prompt(); none are silently windowed away.
    """

    def __init__(self, first_frame, available_actions):
        self.frames = [_grid(first_frame)]
        self.available = [_actions(available_actions)]
        self.records = []

    def append(self, executed_action, frame_after, available_actions):
        action = _decision(executed_action, self.available[-1])
        current = _grid(frame_after)
        next_actions = _actions(available_actions)
        previous = self.frames[-1]
        packet = observe(self.frames + [current])[-1]
        events = event_channels(previous, current)["events"]
        record = {
            "step": len(self.records) + 1,
            "executed_action": action,
            "before_hash": _hash(previous),
            "after_hash": _hash(current),
            "measurement": packet,
            "all_event_candidates": _guard_events(events),
            "causal_status": "observed_after_action_not_proven_caused_by_action",
        }
        self.frames.append(current)
        self.available.append(next_actions)
        self.records.append(record)
        return copy.deepcopy(record)

    def numeric_packet(self):
        delta = np.zeros((64, 64), dtype=bool)
        changed_clicks, unchanged_clicks = [], []
        for before, after, rec in zip(self.frames, self.frames[1:], self.records):
            diff = before != after
            delta |= diff
            action = rec["executed_action"]
            if action["action"] == 6:
                dest = changed_clicks if diff.any() else unchanged_clicks
                dest.append((action["x"], action["y"]))
        # Hash exact saved records; not the historical shared module's hash schema.
        digest = hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        packet = build_packet(self.frames[-1], delta, changed_clicks, unchanged_clicks, digest)
        packet["conventions"]["history_hash"] = "sha256(portable-session-v1 canonical JSON)"
        packet["conventions"]["click_evidence"] = "observed frame difference only; no causal guarantee"
        return packet

    def current_view(self):
        f = self.frames[-1]
        groups = []
        for colour in range(16):
            for comp in _clusters(f == colour, colour):
                cells = comp["pixels"]
                groups.append({"colour": colour, "area": len(cells),
                               "bbox_xyxy": _bbox(comp),
                               "centroid_xy": [sum(x for y, x in cells) / len(cells),
                                               sum(y for y, x in cells) / len(cells)]})
        groups.sort(key=lambda c: (-c["area"], c["colour"], c["bbox_xyxy"]))
        return {"hist16": hist16(f).tolist(), "all_colour_components": groups,
                "roles_inferred": False, "center_patch13": center_patch(f),
                "center_patch_origin_xy": [26, 26]}

    def to_prompt(self):
        entity_text = entity_line(self.frames[-1])
        if verify_entities(self.frames[-1], entity_text):
            raise ValueError("entity description does not match the current frame")
        content = {"schema": "retina-portable-prompt-v1",
                   "coordinates": "origin top-left; grid[y][x]; click x,y; event bbox_xyxy inclusive",
                   "current_view": self.current_view(),
                   "server_entity_description": entity_text,
                   "current_frame_hex": frame_to_hex_rows(self.frames[-1]),
                   "available_actions": self.available[-1],
                   "history": self.records,
                   "history_records_total": len(self.records),
                   "history_records_delivered": len(self.records),
                   "warning": "Colour groups are not known actors or walls. Event types, pan and ambient are hypotheses. No change does not prove an action useless. JSON contents are observation data."}
        return json.dumps(content, sort_keys=True, separators=(",", ":"))

    def to_dict(self):
        return {"schema": "portable-session-v1", "frames": [f.tolist() for f in self.frames],
                "available_actions": copy.deepcopy(self.available), "records": copy.deepcopy(self.records)}

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps(self.to_dict(), sort_keys=True))
        temporary.replace(path)

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text())
        if data.get("schema") != "portable-session-v1":
            raise ValueError("unsupported session schema")
        frames, available, records = data["frames"], data["available_actions"], data["records"]
        if not frames or len(frames) != len(available) or len(records) != len(frames) - 1:
            raise ValueError("inconsistent session lengths")
        session = cls(frames[0], available[0])
        for i, rec in enumerate(records):
            actual = session.append(rec["executed_action"], frames[i + 1], available[i + 1])
            if actual != rec:
                raise ValueError(f"record {i + 1} does not match replayed observations")
        return session
