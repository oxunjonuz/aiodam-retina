# Qwen-assisted public-game research: 164/183 levels

## Summary

Preserved project records support a reported aggregate progress point of **164 of 183 public ARC-AGI-3 levels** in the AIODAM/Qwen research line. The Qwen Code CLI session used `qwen3.8-max`. Its continuation was interrupted by exhaustion of the provider's **weekly token-plan quota**.

This is a public-game research result, not an official blind benchmark score. It is not a claim that Qwen alone solved all 164 levels from scratch: the project reused previously verified solutions and included contributions from other researchers/controllers.

The Retina idea and original implementation were developed by my AI agent, AIODAM. I am publishing its work as the agent's owner, not claiming the idea as my own.

## How the count is supported

The saved records were at different stages of consolidation:

| Record | Recorded progress | Meaning |
| --- | --- | --- |
| Earlier `UNION_MANIFEST.json` | 142/183 | An older machine-readable snapshot, not the last progress record |
| Later `PROGRESS_LEDGER.md` | 159/183 | The last aggregate total written into the progress journal |
| Five separate `lf52` verification reports | Levels 3, 4, 5, 6 and 7 | Five additional levels, each marked `FRESH_REPLAY_PASS` |
| Documentary reconciliation | 159 + 5 = 164/183 | The file-supported progress point; the older union manifest was not updated to this total |

The five reports have empty error lists. Each records a full-prefix replay reaching the claimed level and a negative control where dropping the last action leaves one fewer level completed:

| Additional level | Full replay: completed levels | Drop-last control: completed levels | Recorded verdict |
| --- | --- | --- | --- |
| lf52 L3 | 3 | 2 | FRESH_REPLAY_PASS |
| lf52 L4 | 4 | 3 | FRESH_REPLAY_PASS |
| lf52 L5 | 5 | 4 | FRESH_REPLAY_PASS |
| lf52 L6 | 6 | 5 | FRESH_REPLAY_PASS |
| lf52 L7 | 7 | 6 | FRESH_REPLAY_PASS |

These are archived verification results, inspected for this report on 2026-09-11. No new replay of all 164 levels was performed for this publication. The report does not replace a rebuilt, independently replayed per-level inventory.

## Why the session stopped

The saved CLI telemetry contains 12 quota-related API errors. The first is at **2026-09-04 07:48:33.793 UTC**, and the last at **08:01:14.391 UTC**. Both identify `qwen3.8-max`, HTTP status `429`, and this provider message:

```text
429 Your token-plan 1-week quota has been exhausted. The quota will reset at 09-11 05:12:00 UTC.
```

This establishes a provider usage-quota interruption. It is **not** a context-window overflow, GPU-memory error or game-loss message. It does not prove that the remaining 19 levels would all have been solved with a larger allowance. Nor does the quota message measure the cost of this experiment alone.

## What this says about Retina

The progress journal records a Retina/Grid-JEPA handoff integrity check and its shared coordinate conventions. Retina was part of the research tooling available to Qwen. This is an application record, not an ablation proving that Retina alone caused every success.

The research setting allowed existing solutions, game-source inspection and research tools; it was not restricted to a blind player's observation/action interface. No private evaluation score, VLM superiority claim or AGI claim follows from this result.

The separately measured **98.2% input-token reduction** and **8.202 ms sensor time** concern the historical sensor audit, not this gameplay score. See the [main report](REPORT_EN.md).

## Source fingerprints

Only source basenames and SHA-256 fingerprints are disclosed. Local paths, credentials, private agent memory, full conversations and solution-action files are not included in this report.

```text
PROGRESS_LEDGER.md
b915ea57307bf3847e69f62072110b1dbde17501ec4ef975c3e93b62f2b0662b
UNION_MANIFEST.json
cda60ac234ab037005172fa5bcc044629dd6672f9792f7154e0f45676a6f5694
lf52_l3_independent_verification.json
ed1f598c636025ef0e7d987529c6770ac5a1b1fee98661ad41c4ef098669f8be
lf52_l4_independent_verification.json
2a7fa99ad0c3066112fc5e7d99c3715006d63e630a6aa6bea69698af83bf8a66
lf52_l5_independent_verification.json
a3dc7210baf90b199df274c88e13c74c7f83e4911dd27dce2e8fe29d6e141d3e
lf52_l6_independent_verification.json
4cc9adaf65f96cc5db34149446a4444bfdab53e2f745130fea3060e9b88d2e86
lf52_l7_independent_verification.json
f7394d3a6043d357025a7ed8cff114b91c917d9b512761672123565496b31721
CLI session JSONL (private original; quota events at lines 4043-4070)
22040ae28bbd67b70b89524d3e7b1e967e17fb4adc40445e57ed2c46c616a0ac
```

Fingerprints identify the preserved originals; they are not substitutes for public raw evidence or an independent replay. This report discloses results and evidence boundaries, not AIODAM's private architecture.
