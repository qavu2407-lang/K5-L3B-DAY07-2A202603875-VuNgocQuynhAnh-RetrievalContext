"""Offline benchmark checks (no API): split counts (BENCHMARK.md minimums), gold inside a chunk,
and every absence_checks term has 0 hits in the indexed chunks of its page range.

Run after export_day6.py: .venv/bin/python src/check_benchmark.py   (exits non-zero on failure)
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))
from baseline import validate  # noqa: E402

MINIMUM = {("dev", True): 15, ("dev", False): 2, ("test", True): 5, ("test", False): 2}


def absence_hits(q: dict, chunks: list[dict]) -> list[str]:
    hits = []
    for check in q["absence_checks"]:
        lo, hi = check["pages"]
        for c in chunks:
            if lo <= c["page"] <= hi:
                hits += [f"{t!r} in {c['id']}" for t in check["terms"] if t.casefold() in c["text"].casefold()]
    return hits


def main() -> None:
    chunks = json.loads((ROOT / "data/day6/chunks.json").read_text())
    questions = json.loads((ROOT / "data/day6/questions.json").read_text())
    validate(chunks, [q for q in questions if q["answerable"]])

    counts = Counter((q["split"], q["answerable"]) for q in questions)
    errors = [f"{k}: {counts[k]} < {n}" for k, n in MINIMUM.items() if counts[k] < n]
    for q in questions:
        if not q["answerable"]:
            assert q["expected_behavior"] == "search_and_abstain" and q["absence_reason"] and "gold" not in q, q["id"]
            errors += [f"{q['id']}: {h}" for h in absence_hits(q, chunks)]

    for q in questions:
        print(f"{q['id']:4} {q['split']:4} {q['type']:12} filter={q['filter']}  {q['question']}")
    print({f"{s} {'answerable' if a else 'unanswerable'}": n for (s, a), n in sorted(counts.items())})
    if errors:
        sys.exit("FAIL\n" + "\n".join(errors))
    print("OK")


if __name__ == "__main__":
    main()
