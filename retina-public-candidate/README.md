# AIODAM Retina

Spatial perception, temporal change measurements and action-observation history
for language-model agents working with discrete 64x64 colour grids.

**Local release candidate. Not published. License selection and fixture
redistribution review are pending.** [Russian README](README_RU.md).

English is the primary documentation language. Start with this README and
[the English report](docs/REPORT_EN.md). Russian translations are supplementary.

Retina is more than a binary change mask. Four complementary channels provide:

1. **Global colour sensor:** counts of all 16 colours, histogram differences and
   the number of changed cells.
2. **Current spatial view / fovea:** colour components, positions, extents and a
   local patch, including before the first action.
3. **Temporal event sensor:** colour-membership ON/OFF regions, event geometry,
   candidate displacement, camera-pan and ambient-motion heuristics.
4. **Action-observation history:** what was executed and what was observed after
   it, saved across restarts. A temporal association is not a causal proof.

These channels run alongside one another. ON/OFF maps are an intermediate input
to event matching, not the final output of the entire system.

## Measured evidence

| Measurement | Historical result | Scope |
| --- | --- | --- |
| Mean input tokens | 24,619 -> 441 | Two textual grids vs Retina packet; Qwen2.5 tokenizer; five examples |
| Input-token reduction | 98.2% | Not win rate, recognition accuracy or a VLM A/B result |
| Mean sensor time | 8.202 ms | 500 historical `observe` calls in a disposable container |
| Generator checks | 45/45 | Historical audit |
| Independent packet verification | 5/5 | Rechecked from included frames |
| Corrupted-coordinate rejection | 5/5 | Negative controls |

The compact packet is a **lossy feature representation**, not a lossless encoding
of the entire scene. The full-session example includes more information and is
not claimed to have the same 98.2% reduction or 8.202 ms processing time.

Recorded gameplay applications are separate evidence. See
[the report](docs/REPORT_EN.md) for the distinction between sensor measurements,
blind controller play and Qwen-assisted public-game research.

## Quick start

Python 3.10+ and NumPy are sufficient; no GPU, model weights, API key or game
engine is needed for the included tests and synthetic example.

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python tools/verify_historical_audit.py --eval-root evidence
python examples/demo.py
python tools/benchmark.py
```

The example writes a complete session, the next observation prompt and a
22-channel numeric packet to `demo_output/`. It does not call an LLM.

```python
from retina import RetinaSession

session = RetinaSession(first_public_frame, available_actions)
# Your environment executes the selected action before this call:
session.append(executed_action, resulting_public_frame, next_available_actions)
observation_text = session.to_prompt()
numeric_input = session.numeric_packet()
session.save("game_session.json")
restored = RetinaSession.load("game_session.json")
```

Instantiate a separate session for each game. The portable session retains every
frame and record; its prompt contains the full observation history and current
grid. It never silently clips history to a fixed last-N window. This means memory,
runtime and prompt length grow with the session; the caller must handle model
context limits explicitly. Do not retry by secretly dropping earlier records.

## Contents

- `retina/temporal.py`: byte-identical historical core.
- `retina/spatial_legacy.py`: original spatial functions, with historical limits.
- `retina/event_guard.py`: original event-semantic safeguard.
- `retina/retina_packet.py`: shared coordinate and 22-plane representation.
- `retina/qwen_serializer.py`: historical shared-packet serializer.
- `retina/session.py`: new portable integration and full journal.
- `retina/entities.py`: original server-run entity extraction, explicit X/Y
  descriptions and frame-to-description consistency check; connected to the
  portable session prompt, not just included as unused source.
- `evidence/`: historical measurements, selected real public frames, negative
  controls, source hashes and fresh verification.
- `tests/`, `examples/`, `tools/`: runnable validation and integration examples.
- `docs/`: history, mechanism map, limitations, provenance and release checklist.

## Important boundaries

Colour components are not automatically players, walls or targets. Pan, ambient
masking and event labels are heuristics. The historical event `delta` describes
matched ON/OFF centroids, not necessarily true object velocity. Preserve raw
changes when a filtered channel reports no effect. Retina supplies observations;
reasoning, experiment design, planning and action execution remain external.

No direct VLM superiority claim, private-benchmark score, guaranteed gameplay
success or AGI claim is made. The package has no network calls.

For repository setup, see [Publishing to GitHub](docs/PUBLISHING.md).
