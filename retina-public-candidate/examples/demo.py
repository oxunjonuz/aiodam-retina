"""Synthetic demonstration; not an ARC game, score or historical experiment."""
import json
from pathlib import Path
import numpy as np
from retina import RetinaSession

first = np.zeros((64, 64), dtype=np.int16)
first[12:15, 8:11] = 4
second = np.zeros_like(first)
second[12:15, 9:12] = 4
session = RetinaSession(first, [1, 2, 3, 4, 6])
result = session.append({"action": 4}, second, [1, 2, 3, 4, 6])
Path("demo_output").mkdir(exist_ok=True)
session.save("demo_output/session.json")
Path("demo_output/prompt.json").write_text(session.to_prompt())
np.savez_compressed("demo_output/packet.npz", planes=session.numeric_packet()["planes"])
assert RetinaSession.load("demo_output/session.json").to_dict() == session.to_dict()
print(json.dumps({"changed_pixels": result["measurement"]["global"]["changed_area"],
                  "saved_transitions": len(session.records), "restore": "PASS"}))
