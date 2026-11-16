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


@unittest.skipUnless(__import__("shutil").which("tesseract"), "tesseract not installed")
class TesseractTest(unittest.TestCase):
    def test_reads_printed_chart_text(self):
        import sys
        from pathlib import Path
        crop = Path(__file__).resolve().parents[1] / "data/advanced/crops/p447_fig0.png"
        if not crop.exists():
            self.skipTest("crop not generated")
        sys.path.insert(0, str(crop.parents[3] / "src"))
        try:
            from adv_index import tesseract
        except Exception as e:  # adv_index needs the Day 6 repo (DAY6_DIR)
            self.skipTest(f"adv_index not importable: {e}")
        text, mean, n = tesseract(crop)
        self.assertIn("Poisson", text)
        self.assertGreaterEqual(n, 10)


class ReadFigureTest(unittest.TestCase):
    def _ctrl(self, figures):
        import os
        from agent import OpenAIController
        os.environ.setdefault("OPENAI_API_KEY", "test")
        c = OpenAIController(3, "gpt-4.1-mini", figures=figures)
        c._context_ids = {"ADV:p1:fig0", "ADV:p1:t0"}
        return c

    def test_rejects_ids_outside_context_or_not_figures(self):
        c = self._ctrl({"ADV:p1:fig0": (None, "cap"), "ADV:p9:fig0": (None, "cap")})
        self.assertIn("not in the current context", c._read_figure("ADV:p9:fig0", "q"))
        self.assertIn("not a figure chunk", c._read_figure("ADV:p1:t0", "q"))
        self.assertEqual(c.log, [])  # no vision call was made

    def test_reading_is_logged_with_cost(self):
        import tempfile
        from pathlib import Path
        png = Path(tempfile.mkdtemp()) / "f.png"
        png.write_bytes(b"\x89PNG")
        c = self._ctrl({"ADV:p1:fig0": (png, "Figure 1")})
        c._post = lambda body: {"usage": {"prompt_tokens": 1000, "completion_tokens": 100},
                                "choices": [{"message": {"content": "2022, about -900"}}]}
        self.assertEqual(c._read_figure("ADV:p1:fig0", "lowest year?"), "2022, about -900")
        self.assertEqual(c.log[-1]["tool"], "vision")
        self.assertAlmostEqual(c.log[-1]["cost_usd"], (1000 * 1.0 + 100 * 5.0) / 1e6)


class FigureWordsTest(unittest.TestCase):
    def test_matches_chart_words_only(self):
        from agent import FIGURE_WORDS
        self.assertTrue(FIGURE_WORDS.search("what share of defects ... left of the Pareto chart?"))
        self.assertTrue(FIGURE_WORDS.search("In the heatmap of passengers"))
        self.assertFalse(FIGURE_WORDS.search("According to Table 9.3, which year had the highest enrollment?"))
        self.assertFalse(FIGURE_WORDS.search("Why does the book set d = 2?"))
