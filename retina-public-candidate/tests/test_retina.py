import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from retina import RetinaSession
from retina.event_guard import _guard_events
from retina.retina_packet import build_packet, frame_to_hex_rows, hex_rows_to_frame, bbox_of
from retina.temporal import ambient_mask, event_channels, global_channel, observe


class RetinaTests(unittest.TestCase):
    def setUp(self):
        self.a = np.zeros((64, 64), dtype=np.int16)
        self.a[10:13, 20:23] = 4
        self.b = np.zeros_like(self.a)
        self.b[10:13, 21:24] = 4

    def test_histogram_cannot_detect_translation(self):
        g = global_channel(self.a, self.b)
        self.assertEqual(g["dH1"], 0)
        self.assertEqual(g["changed_area"], 6)

    def test_colour_replacement_has_on_and_off(self):
        b = self.a.copy()
        b[10:13, 20:23] = 9
        e = event_channels(self.a, b)
        self.assertEqual((e["on_px"], e["off_px"]), (9, 9))

    def test_unchanged(self):
        self.assertEqual(observe([self.a, self.a])[0]["global"]["changed_area"], 0)

    def test_first_frame_has_no_fabricated_transition(self):
        s = RetinaSession(self.a, [4])
        self.assertEqual(s.records, [])
        self.assertTrue(s.current_view()["all_colour_components"])

    def test_short_history_not_ambient(self):
        self.assertFalse(ambient_mask([self.a, self.b]).any())

    def test_scene_guard(self):
        e = {"type": "move", "bbox": [0, 0, 63, 63]}
        self.assertEqual(_guard_events([e])[0]["candidate_type"], "scene_transition_candidate")

    def test_event_displacement_is_not_object_motion(self):
        # Partial-overlap ON/OFF strip centroids are 3px apart, although the
        # constructed square translated by 1px. Preserve this known limitation.
        moves = [e for e in event_channels(self.a, self.b)["events"] if e["type"] == "move" and e["colour"] == 4]
        self.assertEqual(moves[0]["delta"], [3.0, 0.0])

    def test_all_colours_preserved(self):
        s = RetinaSession(self.a, [4])
        colours = {c["colour"] for c in s.current_view()["all_colour_components"]}
        self.assertEqual(colours, {0, 4})

    def test_click_xy_planes(self):
        p = build_packet(self.a, effective_clicks=[(51, 7)])
        self.assertEqual(p["planes"][20, 7, 51], 1)
        self.assertEqual(p["planes"][20, 51, 7], 0)

    def test_coordinates(self):
        p = build_packet(self.a)
        self.assertAlmostEqual(float(p["planes"][16, 7, 51]), 51 / 63, places=6)
        self.assertAlmostEqual(float(p["planes"][17, 7, 51]), 7 / 63, places=6)

    def test_numeric_consumer_side_channels(self):
        from retina.retina_packet import packet_to_model_input, SIDE_CHANNELS
        p = build_packet(self.a, effective_clicks=[(51, 7)])
        grid, side = packet_to_model_input(p)
        self.assertEqual(side.shape, (6, 64, 64))
        np.testing.assert_array_equal(grid, self.a)
        np.testing.assert_array_equal(side, np.stack([p["planes"][c] for c in SIDE_CHANNELS]))

    def test_bbox_yxyx(self):
        self.assertEqual(bbox_of(self.a == 4), [10, 20, 12, 22])

    def test_hex_roundtrip(self):
        np.testing.assert_array_equal(hex_rows_to_frame(frame_to_hex_rows(self.a)), self.a)

    def test_no_causal_claim(self):
        s = RetinaSession(self.a, [4])
        r = s.append({"action": 4}, self.b, [4])
        self.assertIn("not_proven", r["causal_status"])

    def test_returned_record_is_copy(self):
        s = RetinaSession(self.a, [4])
        r = s.append({"action": 4}, self.b, [4])
        r["executed_action"]["action"] = 99
        self.assertEqual(s.records[0]["executed_action"]["action"], 4)

    def test_full_history_and_restore(self):
        s = RetinaSession(self.a, [4])
        for _ in range(41):
            s.append({"action": 4}, self.a, [4])
        prompt = json.loads(s.to_prompt())
        self.assertEqual(len(prompt["history"]), 41)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "session.json"
            s.save(path)
            restored = RetinaSession.load(path)
            self.assertEqual(restored.to_dict(), s.to_dict())
            self.assertEqual(restored.to_prompt(), s.to_prompt())

    def test_tampered_record_rejected(self):
        s = RetinaSession(self.a, [4])
        s.append({"action": 4}, self.b, [4])
        data = s.to_dict()
        data["records"][0]["measurement"]["global"]["changed_area"] += 1
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "session.json"
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                RetinaSession.load(path)

    def test_invalid_frames(self):
        for frame in (self.a.astype(float), np.zeros((32, 32), dtype=int), self.a + 16):
            with self.subTest(shape=frame.shape, dtype=frame.dtype):
                with self.assertRaises(ValueError):
                    RetinaSession(frame, [4])

    def test_illegal_action_does_not_mutate(self):
        s = RetinaSession(self.a, [4])
        with self.assertRaises(ValueError):
            s.append({"action": 1}, self.b, [4])
        self.assertEqual(len(s.frames), 1)

    def test_invalid_clicks(self):
        for x in (-1, 64, 1.5, True):
            s = RetinaSession(self.a, [6])
            with self.assertRaises(ValueError):
                s.append({"action": 6, "x": x, "y": 2}, self.b, [6])

    def test_observed_no_change_click(self):
        s = RetinaSession(self.a, [6])
        s.append({"action": 6, "x": 51, "y": 7}, self.a, [6])
        self.assertEqual(s.numeric_packet()["planes"][21, 7, 51], 1)

    def test_imported_serializer(self):
        from retina.qwen_serializer import serialize_observed
        text = serialize_observed(build_packet(self.a), [4])
        self.assertIn("[OBSERVED FRAME]", text)

    def test_server_entity_xy_and_tamper(self):
        from retina.entities import entities, entity_line, verify_entities
        f = np.zeros((64, 64), dtype=np.int16)
        f[7, 51] = 9
        e = next(e for e in entities(f) if e["colour"] == 9)
        self.assertEqual(e["bbox"], [51, 7, 51, 7])
        self.assertEqual(e["centroid"], [51.0, 7.0])
        self.assertEqual(e["pix"], [(7, 51)])
        line = entity_line(f)
        self.assertIn("e:c9@51,7", line)
        self.assertEqual(verify_entities(f, line), [])
        self.assertTrue(verify_entities(f, line.replace("e:c9@51,7", "e:c9@7,51")))

    def test_server_entities_reach_prompt(self):
        from retina.entities import entity_line
        prompt = json.loads(RetinaSession(self.a, [4]).to_prompt())
        self.assertEqual(prompt["server_entity_description"], entity_line(self.a))


if __name__ == "__main__":
    unittest.main()
