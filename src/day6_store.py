"""Dense retrieval on the Day 6 pgvector store, reusing Day 6's own embedder and store classes.

Day 6 repo: https://github.com/qavu2407-lang/K5-L3B-DAY06-2A202603875-DataIngestion
Set DAY6_DIR in .env to a local clone. Errors (API, DB) propagate; there is no mock fallback.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DAY6_DIR = Path(os.environ["DAY6_DIR"]).expanduser()


def _load_day6():
    # Day 6 package is named `src` (clashes with ours) and uses relative imports -> load under alias `day6`.
    pkg = DAY6_DIR / "starter" / "src"
    spec = importlib.util.spec_from_file_location("day6", pkg / "__init__.py", submodule_search_locations=[str(pkg)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["day6"] = mod
    spec.loader.exec_module(mod)


_load_day6()
from day6.embeddings import OpenAIEmbedder  # noqa: E402
from day6.store import PgVectorStore  # noqa: E402

STRATEGY = "B"  # Day 6 paragraph chunks; Day 6 config C = B + chapter filter


def day6_commit() -> str:
    return subprocess.run(["git", "-C", str(DAY6_DIR), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()


def to_day7(row: dict[str, Any], rank: int) -> dict[str, Any]:
    """Day 6 row -> Day 7 chunk contract (data/README.md) + score/rank."""
    return {"id": row["chunk_id"], "text": row["text"], "source_id": row["document_id"],
            "source": row["source"], "page": row["page"],
            "metadata": {**row["metadata"], "chapter": row["chapter"], "sections": list(row["sections"])},
            "score": float(row["score"]), "rank": rank}


class DenseRetriever:
    def __init__(self, model: str = "text-embedding-3-small", strategy: str = STRATEGY) -> None:
        self.embedder = OpenAIEmbedder(model)
        self.store = PgVectorStore(os.environ["DATABASE_URL"], self.embedder.dimensions)
        self.strategy = strategy

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        rows = self.store.search(self.strategy, self.embedder.embed_query(query), top_k=top_k, filters=filters)
        return [to_day7(r, i) for i, r in enumerate(rows, 1)]
