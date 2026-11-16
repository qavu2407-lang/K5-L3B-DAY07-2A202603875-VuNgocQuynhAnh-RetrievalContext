"""Side-by-side table of retrieval runs: summary metrics + per-question first-hit rank.

Run: .venv/bin/python src/compare.py dev dense lexical hybrid  ->  results/dev_comparison.md
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
split, methods = sys.argv[1], sys.argv[2:]
runs = {m: json.loads((ROOT / f"results/{split}-{m}/summary.json").read_text()) for m in methods}
traces = {m: json.loads((ROOT / f"results/{split}-{m}/traces.json").read_text()) for m in methods}

keys = ["hit@1", "evidence_hit@3", "context_evidence_rate", "context_evidence_rate_if_budget_800", "mrr@10",
        "avg_context_chars", "median_ms", "total_s", "embedding_tokens", "cost_usd"]
lines = [f"# Retrieval comparison — {split}", "", "| Metric | " + " | ".join(methods) + " |",
         "|---|" + "---|" * len(methods)]
lines += [f"| {k} | " + " | ".join(str(runs[m][k]) for m in methods) + " |" for k in keys]
lines += ["", "First rank (≤10) at which a chunk containing the gold evidence appears; `-` = not in top 10; "
          "**bold** = within top 3. Unanswerable rows show the top-1 chunk and score.", "",
          "| Q | filter | " + " | ".join(methods) + " |", "|---|---|" + "---|" * len(methods)]
for i, t0 in enumerate(traces[methods[0]]):
    cells = []
    for m in methods:
        t = traces[m][i]
        if not t["answerable"]:
            top = t["results"][0]
            cells.append(f"top1 p{top['page']} ({top['score']:.3f})")
        else:
            r = t["first_hit_rank"]
            cells.append("-" if r is None else (f"**{r}**" if r <= 3 else str(r)))
    lines.append(f"| {t0['query_id']} | {t0['filter'] or ''} | " + " | ".join(cells) + " |")
out = ROOT / f"results/{split}_comparison.md"
out.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
