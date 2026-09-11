# Provenance and modifications

The release candidate is **not entirely a byte-for-byte copy** and is not the
same harness used in historical game runs. This distinction is intentional.

| File | Origin | Changes |
| --- | --- | --- |
| temporal.py | Historical retina_sensor.py | Byte-identical, including existing limitations |
| spatial_legacy.py | Historical extract_v3.py | Three function bodies copied verbatim; data-builder imports and private paths excluded |
| event_guard.py | Historical local_retina.py | `_guard_events` copied verbatim, portable imports and original threshold |
| entities.py | Server-run blind25_mem_semantic.py | `entities`, `entity_line`, `verify_entities` copied verbatim with portable imports; used in the new session prompt |
| retina_packet.py | Shared Retina handoff | Module docstring replaced; one demonstrated NumPy channel-indexing bug fixed |
| qwen_serializer.py | Shared Retina handoff | Module docstring replaced; imports made package-relative |
| session.py | Release preparation, 2026-09-11 | New glue using existing sensor functions, complete journal, validation, persistence |
| verify_historical_audit.py | Independent historical audit | Byte-identical |
| examples/demo.py, tests/test_retina.py, tools/benchmark.py | Release preparation | New synthetic example, regressions, measurement utility |
| evidence/output/audit_report.json | Preserved historical report | Paths redacted; action-label metadata omitted; measurements unchanged |
| evidence/output/artifact_manifest.json | Release preparation | Regenerated for the selected, sanitized evidence; not the original manifest |
| evidence/gameplay_receipts.json | Historical reports | Curated metadata, not full logs or fresh replays |

`evidence/SOURCE_PROVENANCE.json` records source and destination SHA-256 values
and function extraction line ranges. Full unedited originals and local source
paths remain outside the public candidate in the owner's private review folder.

The frozen temporal core SHA-256 is
`53f6cb4ce910bc8f87b27a6a59dc8843014ed22c53c5d8a4c7e422208cb38468`.

The historical measurement tokenizer SHA-256 is
`a8506e7111b80c6d8635951a02eab0f4e1a8e4e5772da83846579e97b16f61bf`.
Tokenizer weights/files are not redistributed. Exact optional re-count requires
the matching tokenizer and the `tokenizers` package. No token count is silently
substituted with character length or another model's tokenizer.

The 22-channel packet is included as a representation, not as learned Grid-JEPA
weights or an affordance model. Historical names such as effective/noop clicks
describe supplied observation labels and do not establish physical causality.
The new session explicitly labels this boundary.

The original `packet_to_model_input` used `planes[SIDE_CHANNELS]` with a tuple
of six integers on a three-dimensional NumPy array, raising `IndexError`.
The candidate uses `planes[list(SIDE_CHANNELS)]` to select six channels on the
first axis. A regression compares every selected plane. The original is retained
outside the candidate; no live agent code was patched.

The entity consistency check regenerates the same description from the frame.
It detects mismatched/stale descriptions, not independent semantic correctness.
An asymmetric-coordinate regression checks X/Y against manually specified pixels.
This extraction does not include the server's entire game executor, training
pipeline or learned spatial head.
