"""Compare agent configs from their traces (+ manual labels if present).

Run: .venv/bin/python src/agent_compare.py dev A0 A1 I1 I2  ->  results/agent_dev_comparison.md
Agent Context Evidence Rate = answerable questions whose FINAL context contains a gold-evidence chunk / answerable.
"""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))
from baseline import hit  # noqa: E402

split, configs = sys.argv[1], sys.argv[2:]
chunks = {c["id"]: c for c in json.loads((ROOT / "data/day6/chunks.json").read_text())}
gold = {q["id"]: q.get("gold") for q in json.loads((ROOT / "data/day6/questions.json").read_text())}


def stats(cfg: str) -> dict:
    d = ROOT / f"results/agent-{split}-{cfg}"
    traces, s = json.loads((d / "traces.json").read_text()), json.loads((d / "summary.json").read_text())
    m = json.loads((d / "metrics.json").read_text()) if (d / "metrics.json").exists() else None
    repeated = added = 0
    ctx_hit = []
    for t in traces:
        searches = [e for e in t["events"] if e["event"] == "search"]
        qs = [" ".join(e["query"].casefold().split()) for e in searches]
        repeated += len(qs) - len(set(qs))
        for a, b in zip(searches, searches[1:]):
            added += len(set(b["context_ids"]) - set(a["context_ids"]))
        if gold[t["query_id"]]:
            final = searches[-1]["context_ids"] if searches else []
            ctx_hit.append(t["query_id"] if any(hit(chunks[i], gold[t["query_id"]]) for i in final) else None)
    n = len(ctx_hit)
    row = {"config": cfg, "retriever": s["retriever"], "budget": s["budget_chars"],
           "distinct_queries": s.get("distinct_queries", False),
           "repeated_queries": repeated, "chunks_added_by_later_searches": added,
           "agent_CER": f"{sum(x is not None for x in ctx_hit)}/{n}",
           "missing_gold_in_context": [q for q, x in zip([t['query_id'] for t in traces if gold[t['query_id']]], ctx_hit) if x is None],
           "searches": s["searches_distribution"], "model_calls": s["model_calls"], "repairs": s.get("repairs", 0),
           "cost_usd": s["llm_cost_usd"], "cost_per_q": round(s["llm_cost_usd"] / s["questions"], 5),
           "median_s": s["median_s_per_question"], "errors": s["status"].get("error", 0)}
    if m:
        g = m["grounded_answer"]
        row |= {"grounded_0/1/2": f"{g['0']}/{g['1']}/{g['2']}", "grounded_mean": round(g["mean"], 2),
                "citation_valid": f"{m['citation_validity']['n']}/{m['citation_validity']['N']}",
                "abstention": f"{m['abstention']['n']}/{m['abstention']['N']}",
                "false_abstention": f"{m['false_abstention']['n']}/{m['false_abstention']['N']}"}
    return row


rows = [stats(c) for c in configs]
keys = list(dict.fromkeys(k for r in rows for k in r))
lines = [f"# Agent comparison — {split}", "", "| | " + " | ".join(r["config"] for r in rows) + " |",
         "|---|" + "---|" * len(rows)]
lines += [f"| {k} | " + " | ".join(str(r.get(k, "")) for r in rows) + " |" for k in keys if k != "config"]
out = ROOT / f"results/agent_{split}_comparison.md"
out.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
