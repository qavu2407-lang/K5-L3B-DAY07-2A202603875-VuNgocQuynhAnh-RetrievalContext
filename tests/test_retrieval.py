"""Offline checks for src/retrieval.py: RRF order, chapter filter, test-split guard."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from retrieval import LexicalRetriever, rrf  # noqa: E402

CHUNKS = [{"id": f"c{i}", "text": t, "source_id": "s", "source": "s.pdf", "page": i, "metadata": {"chapter": ch}}
          for i, (t, ch) in enumerate([("sample space outcomes", 1), ("sample space events", 3), ("median mean", 3)])]


class RetrievalTest(unittest.TestCase):
    def test_rrf_rewards_agreement(self):
        a = [{"id": "x"}, {"id": "y"}, {"id": "z"}]
        b = [{"id": "y"}, {"id": "z"}, {"id": "x"}]
        self.assertEqual([c["id"] for c in rrf([a, b], top_k=3)], ["y", "x", "z"])  # y: 1/62+1/61 is highest

    def test_filter_excludes_other_chapters(self):
        r = LexicalRetriever(CHUNKS)
        self.assertEqual([c["id"] for c in r.search("sample space", filters={"chapter": 3})], ["c1"])
        self.assertEqual(len(r.search("sample space", filters=None)), 2)

    def test_test_split_needs_confirmation(self):
        p = subprocess.run([sys.executable, str(ROOT / "src/retrieval.py"), "--method", "lexical", "--split", "test"],
                           capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("refusing", p.stderr)


if __name__ == "__main__":
    unittest.main()
