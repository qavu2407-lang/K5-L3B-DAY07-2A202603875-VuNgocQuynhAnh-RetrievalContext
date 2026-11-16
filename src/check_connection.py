"""Prove the Day 7 dense retriever reproduces Day 6: same top-3 chunk IDs for every Day 6 question (strategy B).

Run after export_day6.py: .venv/bin/python src/check_connection.py  ->  results/connection_check.json
Exits non-zero on any mismatch or invalid gold.
"""
import json
import sys
import time
from importlib.metadata import version

from day6_store import DAY6_DIR, ROOT, STRATEGY, DenseRetriever, day6_commit

sys.path.insert(0, str(ROOT / "starter"))
from baseline import validate  # noqa: E402


def main() -> None:
    chunks = json.loads((ROOT / "data/day6/chunks.json").read_text())
    questions = json.loads((ROOT / "data/day6/questions.json").read_text())
    validate(chunks, [q for q in questions if q.get("answerable", True)])  # raises if a gold quote isn't inside a chunk

    day6 = {}
    for line in (DAY6_DIR / "starter/results/traces.jsonl").read_text().splitlines():
        t = json.loads(line)
        if t["strategy"] == STRATEGY:
            day6[t["id"]] = [h["chunk_id"] for h in t["hits"][:3]]

    r = DenseRetriever()
    rows, t0 = [], time.perf_counter()
    for q in (q for q in questions if q["id"] in day6):  # unanswerable Qs were added in Day 7, no Day 6 trace
        ours = [c["id"] for c in r.search(q["question"], filters=None, top_k=3)]  # B = no filter, as Day 6 ran it
        rows.append({"id": q["id"], "match": ours == day6[q["id"]], "day7": ours, "day6": day6[q["id"]]})
    elapsed = time.perf_counter() - t0

    report = {"day6_commit": day6_commit(), "strategy": STRATEGY, "embedding_model": r.embedder.model_name,
              "dimensions": r.embedder.dimensions, "store": r.store.versions(), "psycopg": version("psycopg"),
              "chunks": len(chunks), "questions": len(rows),
              "top3_match": f"{sum(x['match'] for x in rows)}/{len(rows)}",
              "query_tokens": r.embedder.tokens_used, "cost_usd": round(r.embedder.cost_usd, 6),
              "search_seconds_total": round(elapsed, 2), "per_question": rows}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/connection_check.json").write_text(json.dumps(report, indent=1) + "\n")
    print({k: v for k, v in report.items() if k != "per_question"})
    if not all(x["match"] for x in rows):
        sys.exit("top-3 mismatch: " + ", ".join(x["id"] for x in rows if not x["match"]))


if __name__ == "__main__":
    main()
