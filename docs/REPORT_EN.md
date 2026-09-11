# Retina: mechanisms, history and evidence

Prepared 2026-09-11 from local source and preserved artifacts. No new game score
was produced during release preparation.

## Origin and development

The project owner proposed taking inspiration from the human eye and visual
system. Retina grew from that idea through joint work with the AIODAM agent,
which contributed research, implementation and testing. The concept was not
entirely originated by the agent. See [provenance](PROVENANCE.md).

## Purpose and four channels

A text model needs more than a colour inventory: it needs positions, geometry,
changes over time, and a record of its own actions. The package supplies these
measurements for 16-colour 64x64 public grids without a learned vision encoder.

**Global colour sensor.** `hist16` counts colour membership; `global_channel`
reports histogram delta, its L1 norm and changed-cell count. A translation can
preserve the histogram, which makes the spatial channel necessary.

**Current spatial view / fovea.** Historical component and centre-patch functions
give the model geometry before it has acted. The original extractor assumes
colour zero is background, uses eight-connected components, omits singletons
and keeps eight components. Those assumptions remain visible in the legacy file.
The new portable session uses the existing four-connected cluster routine for
all colours, retains all components and includes the exact current hex grid.
It does not label components as actors, walls or goals.

The candidate also includes the exact `entities`, `entity_line` and
`verify_entities` function bodies used by the preserved server-run semantic
module. Their description is delivered in the portable session's prompt.
This covers explicit cell X/Y, inclusive XYXY boxes, centroids and component
mask fingerprints. Movement directions remain geometric observations, not
fixed meanings assigned to ACTION1-ACTION7.

**Event Retina.** For each colour, ON means a cell acquired that colour and OFF
means it lost it. A recolour produces both. Clusters are matched by colour and
proximity to produce candidate motion, appearance/disappearance, extents and
centroid differences. Pan and ambient masking are additional heuristics. A guard
labels large matched moves as possible scene transitions. ON/OFF is intermediate
data for event geometry, not the system's final binary answer.

**Action-observation history.** Records link a preceding frame, an executed
action and the resulting observation. The historical short history later became
game-level memory. The private game harness is not bundled; a new, explicitly
labelled portable session provides persistence and complete history delivery.
Observed-after-action is not proof of caused-by-action. Timers, animation and
camera effects require distinguishing experiments before causal attribution.

## Historical sequence

- Early spatial extraction: histogram, component geometry and 13x13 centre patch.
- 2026-08-27: global/event proposal, temporal core, counterexample battery and
  independent real-transition audit.
- 2026-08-27: separate blind controller session using public frames and Retina;
  its archived report records 67 actions, two sc25 level advances and replay
  67/67. This game replay was not rerun for the release candidate.
- 2026-09-01: the recovered bundle documents all four channels and an integration
  defect where a historical prompt omitted current spatial geometry.
- 2026-09-03: shared Qwen/Grid-JEPA coordinate and 22-plane packet handoff.
- 2026-09-04: Qwen CLI journal records handoff checks and verified public-game
  solutions. The inspected ledger reaches a union of 159/183; an older manifest
  still says 142. The previously reported 164 requires reconciling five additional
  levels; that total was not independently rebuilt during this packaging task.
- 2026-09-11: this portable candidate, examples, added tests and documentation.

## Efficiency evidence

Five representative transitions were selected from 31 replayed transitions in
five games. The exact local Qwen2.5 tokenizer counted two textual grids at 24,619
tokens and the Retina-only representation at approximately 441 (350-489).
That is a **98.2% input-token reduction** for the tested representation. Adding
a 24x24 textual crop cost approximately 2,202 tokens, a 91.1% reduction.

This is not recognition accuracy, win rate, total inference speedup, or a direct
comparison against a VLM's image-token encoding. A compact feature packet is
lossy. Comparing with full-grid hex or RLE encoding would be another experiment.

The historical core took 4.100995 seconds for 500 `observe` calls: 8.20199 ms
each. That measured sensor work in a disposable container, not the full LLM/game
pipeline. The included fresh benchmark uses selected frame pairs rather than
the historical context windows; its timing must be reported separately.

Historical checks: 45/45 generator checks, 5/5 independent canonical-packet
checks and 5/5 rejected coordinate-tampered packets. The preserved verifier can
run against the sanitized evidence in this candidate. The report is explicitly
derived; private path fields and unnecessary action-label metadata are removed.
The unmodified report and its hashes remain in the owner's local archive.

## Gameplay evidence is separate

The sc25 controller session and Qwen CLI public-game research demonstrate uses
of the interface, not a controlled estimate of Retina's contribution to wins.
The Qwen ledger explicitly describes an evaluator/teacher-oracle research line;
its union includes previously accumulated solutions from multiple research
branches. It is not an official blind score or proof that Retina alone made a
single Qwen solve all 164 levels. No full solution routes are shipped here.

Three questions must remain distinct: does the representation reduce context;
can it be used in successful problem solving; and how much does it improve win
rate with other variables controlled? The first two have separate evidence.
The third needs a matched A/B evaluation, including a VLM arm if that comparison
is to be claimed.

## Known limits

The original displacement is the separation of matched ON/OFF centroids, not
necessarily object displacement. A one-pixel translated square can generate
strips three pixels apart; a regression test preserves this counterexample.
Same-colour objects can be mismatched. Ambient masking can suppress real repeated
motion. The historic core keeps six event summaries; the new session separately
retains all event candidates. The historical serializer limits region summaries;
it is not used to truncate the new session's full journal.

No visible change does not establish an impassable wall or useless action.
Original event boxes use inclusive XYXY, shared packets inclusive YXYX, explicitly
labelled and tested. The portable entry point validates integer grids; historical
helpers retain their original assumptions. Full history grows in memory, prompt
length and processing cost. No infinite-context guarantee is made.

## Release scope

The candidate contains the four perception/history channels, a shared numeric
packet, serializers, tests, example code and selected public frame evidence.
It excludes AIODAM's private agent runtime, memory, credentials, weights,
training corpora, search solvers and full winning routes. Rights to redistribute
fixtures must be settled before public publication. The code is offered under
PolyForm Noncommercial 1.0.0, with a separate paid commercial licensing route;
see `../LICENSE`, `../NOTICE.md` and `../COMMERCIAL_LICENSE.md`.
The repository is staged at `oxunjonuz/aiodam-retina`.
