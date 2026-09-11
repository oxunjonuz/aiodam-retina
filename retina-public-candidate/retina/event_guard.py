"""Original scene-change safeguard, extracted without AIODAM tool dependencies."""
from typing import Any
SCENE_TRANSITION_BBOX_FRAC = 0.50

def _guard_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    guarded = []
    for event in events:
        x0, y0, x1, y1 = event["bbox"]
        bbox_fraction = ((x1 - x0 + 1) * (y1 - y0 + 1)) / float(64 * 64)
        sensor_type = str(event["type"])
        if sensor_type == "move" and bbox_fraction > SCENE_TRANSITION_BBOX_FRAC:
            candidate_type = "scene_transition_candidate"
            reason = "move matcher covered more than half of the frame"
        else:
            candidate_type = sensor_type + "_candidate"
            reason = "low-level colour membership geometry only"
        guarded.append(
            {
                **{key: value for key, value in event.items() if key != "type"},
                "sensor_type": sensor_type,
                "candidate_type": candidate_type,
                "bbox_fraction": round(bbox_fraction, 6),
                "semantic_label_trusted": False,
                "guard_reason": reason,
            }
        )
    return guarded

