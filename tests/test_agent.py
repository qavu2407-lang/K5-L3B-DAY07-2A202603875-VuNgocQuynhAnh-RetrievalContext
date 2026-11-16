"""Offline checks for src/agent.py: tool-call parsing never guesses."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent import UnseenRetriever, repeated, to_action, unbracketed  # noqa: E402


class FixedRetriever:
    def search(self, query, *, filters=None, top_k=3):
        return [{"id": f"c{i}"} for i in range(top_k)]


def msg(name, **args):
    return {"tool_calls": [{"function": {"name": name, "arguments": json.dumps(args)}}]}


class AgentParseTest(unittest.TestCase):
    def test_search(self):
        self.assertEqual(to_action(msg("search", query="sample space")), ({"action": "search", "query": "sample space"}, "search"))

    def test_answer(self):
        action, tool = to_action(msg("answer", answer="X [c1]", citations=["c1"]))
        self.assertEqual((action["action"], action["citations"], tool), ("answer", ["c1"], "answer"))

    def test_abstain_has_no_citations(self):
        action, tool = to_action(msg("abstain", reason="not in book"))
        self.assertEqual((action["citations"], tool), ([], "abstain"))

    def test_unbracketed_detects_missing_inline_ids(self):
        self.assertEqual(unbracketed({"action": "answer", "answer": "X [c1].", "citations": ["c1", "c2"]}), ["c2"])
        self.assertEqual(unbracketed({"action": "search", "query": "q"}), [])

    def test_repeated_query_ignores_case_and_spaces(self):
        self.assertTrue(repeated({"action": "search", "query": "Run  ALL"}, ["run all"]))
        self.assertFalse(repeated({"action": "search", "query": "run before"}, ["run all"]))
        self.assertFalse(repeated({"action": "answer", "answer": "x", "citations": []}, ["x"]))

    def test_unseen_retriever_returns_next_best(self):
        r = UnseenRetriever(FixedRetriever())
        self.assertEqual([c["id"] for c in r.search("q")], ["c0", "c1", "c2"])
        self.assertEqual([c["id"] for c in r.search("q")], ["c3", "c4", "c5"])

    def test_malformed_raises(self):
        for bad in ({"content": "plain text"}, {"tool_calls": []},
                    {"tool_calls": [{"function": {"name": "search", "arguments": "{oops"}}]}, msg("delete_db")):
            with self.assertRaises((ValueError, KeyError)):
                to_action(bad)


class TypedSearchTest(unittest.TestCase):
    def test_tag_and_filter(self):
        from agent import TypedRetriever
        action, _ = to_action(msg("search", query="kayak revenue", content_type="table"))
        self.assertEqual(action["query"], "kayak revenue ||type=table")

        class Mixed:
            def search(self, query, *, filters=None, top_k=3):
                assert "||" not in query
                return [{"id": f"c{i}", "metadata": {"type": "table" if i % 2 else "text"}} for i in range(top_k)]
        rows = TypedRetriever(Mixed()).search("q ||type=table", top_k=2)
        self.assertEqual([r["id"] for r in rows], ["c1", "c3"])


class SplitGroupedTest(unittest.TestCase):
    def test_only_listed_ids_are_split(self):
        from agent import split_grouped
        a = {"answer": "X [a, b] and Y [a | b] but [see note, c]", "citations": ["a", "b"]}
        self.assertEqual(split_grouped(a), "X [a][b] and Y [a][b] but [see note, c]")

    def test_append_missing_only_adds_unwritten_ids(self):
        from agent import append_missing
        self.assertEqual(append_missing({"action": "answer", "answer": "X [a]. ", "citations": ["a", "b"]}), "X [a]. [b]")
        self.assertEqual(append_missing({"action": "answer", "answer": "X [a]", "citations": ["a"]}), "X [a]")

class CalculatorTest(unittest.TestCase):
    def test_arithmetic_only(self):
        from agent import safe_eval
        self.assertAlmostEqual(safe_eval("(1543 + 1410 + 1348) / 5,635 * 100"), 76.3265, places=3)
        for bad in ("__import__('os')", "open('x')", "2 ** 999"):
            with self.assertRaises(Exception):
                safe_eval(bad)


class ContextBlocksTest(unittest.TestCase):
    def test_blocks_keep_blank_lines(self):
        from agent import context_blocks
        ctx = "[A:p1:fig0 | s.pdf | page 1]\nFigure 1\n\n2. axis\n\n[A:p2:t0 | s.pdf | page 2]\ntext"
        b = context_blocks(ctx)
        self.assertEqual(list(b), ["A:p1:fig0", "A:p2:t0"])
        self.assertIn("2. axis", b["A:p1:fig0"])


if __name__ == "__main__":
    unittest.main()
