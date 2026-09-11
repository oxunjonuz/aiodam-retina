"""Remeasure frozen temporal core; optional exact historical tokenizer counts."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
from retina.temporal import observe

parser = argparse.ArgumentParser()
parser.add_argument("--calls", type=int, default=500)
parser.add_argument("--tokenizer", type=Path)
args = parser.parse_args()
if args.calls <= 0:
    parser.error("calls must be positive")
root = Path(__file__).resolve().parents[1] / "evidence/output"
cases = sorted(p for p in root.iterdir() if p.is_dir())
pairs = [[np.load(p / name, allow_pickle=False) for name in ("previous.npy", "current.npy")] for p in cases]
start = time.perf_counter()
for i in range(args.calls):
    observe(pairs[i % len(pairs)])
elapsed = time.perf_counter() - start
out = {"scope": "frozen temporal observe only; not LLM response or full session", "calls": args.calls,
       "elapsed_seconds": elapsed, "mean_milliseconds": 1000 * elapsed / args.calls}
if args.tokenizer:
    import hashlib
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(args.tokenizer))
    out["tokenizer_sha256"] = hashlib.sha256(args.tokenizer.read_bytes()).hexdigest()
    rows = []
    for p in cases:
        prompts = json.loads((p / "prompts.json").read_text())
        rows.append({k: len(tokenizer.encode(v).ids) for k, v in prompts.items() if k != "warning"})
    out["token_counts"] = rows
print(json.dumps(out, indent=2))
