"""Check the advanced benchmark (data/advanced/benchmark.json) against ADVANCED.md and the index.

Run after `adv_index.py extract`: .venv/bin/python src/adv_check.py   (exits non-zero on failure)
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_MIN = {"table": 6, "image": 5, "chart": 5, "multihop": 4, "text": 4, "unanswerable": 6}
TEST_TOTAL, DEV_ANSWERABLE, DEV_UNANSWERABLE = 30, 15, 3


def main() -> None:
    qs = json.loads((ROOT / "data/advanced/benchmark.json").read_text())
    chunks = json.loads((ROOT / "data/advanced/chunks.json").read_text())
    pages = {c["page"] for c in chunks}
    kinds = {(c["page"], c["metadata"]["type"]) for c in chunks}
    errors = []

    ids = [q["id"] for q in qs]
    if len(ids) != len(set(ids)):
        errors.append("duplicate id")
    test = [q for q in qs if q["split"] == "test"]
    dev = [q for q in qs if q["split"] == "dev"]
    tg = Counter(q["group"] for q in test)
    errors += [f"test {g}: {tg[g]} < {n}" for g, n in TEST_MIN.items() if tg[g] < n]
    if len(test) < TEST_TOTAL:
        errors.append(f"test total {len(test)} < {TEST_TOTAL}")
    if sum(q["answerable"] for q in dev) < DEV_ANSWERABLE or sum(not q["answerable"] for q in dev) < DEV_UNANSWERABLE:
        errors.append("dev counts below minimum")
    if len({q["question"].casefold() for q in qs}) != len(qs):
        errors.append("duplicate question text")

    for q in qs:
        if q["answerable"]:
            assert q["group"] != "unanswerable" and q["expected_answer"] and q["evidence"], q["id"]
            for e in q["evidence"]:
                if e["page"] not in pages:
                    errors.append(f"{q['id']}: evidence page {e['page']} not indexed")
                elif (e["page"], e["kind"]) not in kinds:
                    errors.append(f"{q['id']}: no {e['kind']} chunk on page {e['page']} (check extraction)")
            if q["group"] == "multihop" and len({e["page"] for e in q["evidence"]}) < 2:
                errors.append(f"{q['id']}: multihop needs evidence from >= 2 pages")
        else:
            assert q["expected_behavior"] == "search_and_abstain" and q["absence_reason"], q["id"]
            for chk in q["absence_checks"]:
                lo, hi = chk["pages"]
                for c in chunks:
                    if lo <= c["page"] <= hi:
                        text = f" {c['text'].casefold()} "
                        for t in chk["terms"]:
                            if re.search(re.escape(t.casefold()), text):
                                errors.append(f"{q['id']}: {t!r} found in {c['id']}")

    print({"dev": dict(Counter(q["group"] for q in dev)), "test": dict(tg), "total": len(qs)})
    if errors:
        sys.exit("FAIL\n" + "\n".join(errors))
    print("OK")


if __name__ == "__main__":
    main()
