"""Three retrieval methods on the same Day 6 corpus (strategy B, 524 chunks) + dev/test evaluation.

  dense   - Day 6 pgvector exact cosine (src/day6_store.py)
  lexical - TF-IDF from starter/baseline.py
  hybrid  - Reciprocal Rank Fusion of dense top-20 + lexical top-20 (ranks only, no score mixing)

Run: .venv/bin/python src/retrieval.py --method dense --split dev
Writes results/<split>-<method>/{traces,summary}.json. Gold is used only to score, never in the query.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))
from baseline import TfidfIndex, hit, pack_context  # noqa: E402

BUDGET = 3200  # chars incl. source headers; see report for why not the starter's 800
TOP_K = 3      # Hit@1 / Evidence Hit@3 / context are computed on the top 3
TRACE_K = 10   # ranks kept in the trace (MRR@10)
POOL = 20      # candidates per retriever fed into RRF
RRF_K = 60


def allowed(chunk: dict, filters: dict | None) -> bool:
    return all(chunk["metadata"].get(k) == v for k, v in (filters or {}).items())


class LexicalRetriever:
    def __init__(self, chunks: list[dict]) -> None:
        self.index = TfidfIndex(chunks)  # IDF over the whole corpus; filter applied after scoring
        self.n = len(chunks)

    def search(self, query: str, *, filters: dict | None = None, top_k: int = TOP_K) -> list[dict]:
        rows = [c for c in self.index.search(query, top_k=self.n) if allowed(c, filters)][:top_k]
        return [{**c, "rank": i} for i, c in enumerate(rows, 1)]


def rrf(ranked_lists: list[list[dict]], top_k: int, k: int = RRF_K) -> list[dict]:
    """score(chunk) = sum over lists of 1 / (k + rank). Ties broken by id for determinism."""
    score, chunk = {}, {}
    for rows in ranked_lists:
        for rank, c in enumerate(rows, 1):
            score[c["id"]] = score.get(c["id"], 0.0) + 1 / (k + rank)
            chunk.setdefault(c["id"], c)
    ids = sorted(score, key=lambda i: (-score[i], i))[:top_k]
    return [{**chunk[i], "score": score[i], "rank": r} for r, i in enumerate(ids, 1)]


class HybridRetriever:
    def __init__(self, dense, lexical) -> None:
        self.dense, self.lexical = dense, lexical

    def search(self, query: str, *, filters: dict | None = None, top_k: int = TOP_K) -> list[dict]:
        lists = [r.search(query, filters=filters, top_k=POOL) for r in (self.dense, self.lexical)]
        return rrf(lists, top_k)


def make(method: str, chunks: list[dict], strategy: str = "B"):
    if method == "lexical":
        return LexicalRetriever(chunks)
    from day6_store import DenseRetriever  # lazy: needs .env, DB and OpenAI
    dense = DenseRetriever(strategy=strategy)  # "B" = Day 6 ch.1-3, "ADV" = advanced ch.5/6/9
    return dense if method == "dense" else HybridRetriever(dense, LexicalRetriever(chunks))


def evaluate(retriever, questions: list[dict], method: str, budget: int = BUDGET) -> list[dict]:
    traces = []
    for q in questions:
        t0 = time.perf_counter()
        results = retriever.search(q["question"], filters=q.get("filter"), top_k=TRACE_K)
        ms = (time.perf_counter() - t0) * 1000
        top = results[:TOP_K]
        context, ids = pack_context(top, budget)
        _, ids800 = pack_context(top, 800)  # diagnostic only: what the starter default would keep
        gold = q.get("gold") or []
        marked = [{"id": c["id"], "page": c["page"], "chapter": c["metadata"].get("chapter"),
                   "score": round(c["score"], 6), "rank": c["rank"], "hit": hit(c, gold)} for c in results]
        first = next((m["rank"] for m in marked if m["hit"]), None)
        traces.append({
            "query_id": q["id"], "split": q["split"], "answerable": q["answerable"], "question": q["question"],
            "query": q["question"], "filter": q.get("filter"), "method": method, "results": marked,
            "context": context, "context_ids": ids, "context_chars": len(context),
            "dropped_from_context": [c["id"] for c in top if c["id"] not in ids], "elapsed_ms": round(ms, 1),
            "hit1": bool(marked and marked[0]["hit"]), "hit3": any(m["hit"] for m in marked[:TOP_K]),
            "context_hit": any(m["hit"] and m["id"] in ids for m in marked[:TOP_K]),
            "context_hit_at_800": any(m["hit"] and m["id"] in ids800 for m in marked[:TOP_K]),
            "first_hit_rank": first})
    return traces


def summarize(traces: list[dict], method: str, split: str, tokens: int, cost: float) -> dict:
    ans = [t for t in traces if t["answerable"]]
    n = len(ans)
    frac = lambda k: f"{sum(t[k] for t in ans)}/{n} ({100 * sum(t[k] for t in ans) / n:.1f}%)"  # noqa: E731
    return {"method": method, "split": split, "questions": len(traces), "answerable_N": n,
            "hit@1": frac("hit1"), "evidence_hit@3": frac("hit3"), "context_evidence_rate": frac("context_hit"),
            "context_evidence_rate_if_budget_800": frac("context_hit_at_800"),
            "mrr@10": round(sum(1 / t["first_hit_rank"] for t in ans if t["first_hit_rank"]) / n, 3),
            "context_budget": f"{BUDGET} chars (incl. headers)",
            "avg_context_chars": round(statistics.mean(t["context_chars"] for t in traces)),
            "questions_with_dropped_chunks": sum(bool(t["dropped_from_context"]) for t in traces),
            "median_ms": statistics.median(t["elapsed_ms"] for t in traces),
            "total_s": round(sum(t["elapsed_ms"] for t in traces) / 1000, 2),
            "embedding_tokens": tokens, "cost_usd": round(cost, 6),
            "settings": {"top_k": TOP_K, "trace_k": TRACE_K, "rrf_pool": POOL, "rrf_k": RRF_K,
                         "filter": "question-supplied chapter only", "query": "original question"}}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--method", required=True, choices=("dense", "lexical", "hybrid"))
    p.add_argument("--split", required=True, choices=("dev", "test"))
    p.add_argument("--confirm-frozen", action="store_true", help="required for --split test")
    a = p.parse_args()
    if a.split == "test" and not a.confirm_frozen:
        sys.exit("refusing to run test: freeze the config on dev first, then pass --confirm-frozen")
    chunks = json.loads((ROOT / "data/day6/chunks.json").read_text())
    questions = [q for q in json.loads((ROOT / "data/day6/questions.json").read_text()) if q["split"] == a.split]
    r = make(a.method, chunks)
    traces = evaluate(r, questions, a.method)
    emb = getattr(r, "embedder", None) or getattr(getattr(r, "dense", None), "embedder", None)
    summary = summarize(traces, a.method, a.split, emb.tokens_used if emb else 0, emb.cost_usd if emb else 0.0)
    out = ROOT / "results" / f"{a.split}-{a.method}"
    out.mkdir(parents=True, exist_ok=True)
    for name, obj in (("traces.json", traces), ("summary.json", summary)):
        (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "settings"}, indent=1))


if __name__ == "__main__":
    main()
