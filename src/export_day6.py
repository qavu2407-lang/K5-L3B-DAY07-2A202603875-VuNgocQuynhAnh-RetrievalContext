"""Export Day 6 strategy-B chunks and the 20 Day 6 questions (+ data/unanswerable.json) to the Day 7 JSON contract.

Run: .venv/bin/python src/export_day6.py   ->  data/day6/chunks.json, data/day6/questions.json
"""
import json
import os

import psycopg
from psycopg.rows import dict_row

from day6_store import DAY6_DIR, ROOT, STRATEGY, to_day7

OUT = ROOT / "data" / "day6"


def question(q: dict) -> dict:
    # alternative_evidence (e.g. d15 p30) becomes extra gold entries; starter/convert_day6.py would drop it.
    gold = [{"source_id": q["gold_source_id"], "page": q["gold_page"], "evidence": q["evidence_quote"]}]
    gold += [{"source_id": q["gold_source_id"], "page": a["gold_page"], "evidence": a["evidence_quote"]}
             for a in q.get("alternative_evidence", [])]
    return {"id": q["id"], "split": q["split"], "type": q["type"], "question": q["question"], "answerable": True,
            "expected_answer": q["expected_answer"], "gold": gold, "filter": q["filter"]}


def main() -> None:
    with psycopg.connect(os.environ["DATABASE_URL"]) as c, c.cursor(row_factory=dict_row) as cur:
        rows = cur.execute("""SELECT chunk_id, document_id, source, page, chapter, sections, text, metadata, 0 AS score
                              FROM chunks WHERE strategy = %s ORDER BY page, chunk_id""", (STRATEGY,)).fetchall()
    chunks = [{k: v for k, v in to_day7(r, 0).items() if k not in ("score", "rank")} for r in rows]
    questions = [question(q) for q in json.loads((DAY6_DIR / "benchmark" / "questions.json").read_text())]
    questions += json.loads((ROOT / "data" / "unanswerable.json").read_text())  # hand-written, see absence_reason
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids)), "duplicate question id"
    assert all(q["split"] in ("dev", "test") for q in questions), "split must be dev/test"
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in (("chunks.json", chunks), ("questions.json", questions)):
        (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(chunks)} chunks, {len(questions)} questions -> {OUT}")


if __name__ == "__main__":
    main()
