"""Advanced challenge: index chapters 5, 6, 9 of the textbook (text + tables + figures) into pgvector (strategy ADV).

Run:  .venv/bin/python src/adv_index.py extract   -> data/advanced/{chunks.json, index_report.json, crops/*.png}
      .venv/bin/python src/adv_index.py embed     -> upsert into Day 6 pgvector, strategy "ADV"
      .venv/bin/python src/adv_index.py ocr       -> data/advanced/{chunks_ocr.json, ocr_report.json} (OCR variant)
      .venv/bin/python src/adv_index.py embed chunks_ocr.json ADVOCR
Figure descriptions come from gpt-4.1-mini vision and are cached in data/advanced/figures.json (re-runs do not
call the model again). They are model output: benchmark figures are checked against the PDF by hand.
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pymupdf

from day6_store import DAY6_DIR, ROOT  # loads .env and the Day 6 package as `day6`

PDF = DAY6_DIR / "data" / "Principles-of-Data-Science-WEB.pdf"
SOURCE_ID, SOURCE = "openstax-pds-2025", "data/Principles-of-Data-Science-WEB.pdf"
# content pages: chapter start up to (not incl.) the "Key Terms" outline entry (same rule as Day 6)
CHAPTERS = {5: (223, 267, 274), 6: (275, 335, 340), 9: (421, 466, 470)}  # (first, last content, chapter end)
OUT = ROOT / "data" / "advanced"
MIN_FIG = 60          # pt; smaller images are icons (e.g. the Python logo in code boxes)
MAX_CHARS = 1000      # text chunk size, like Day 6 B
VISION_MODEL, PRICE = "gpt-4.1-mini", (0.40, 1.60)
NOISE = re.compile(r"^(Access for free at openstax\.org|\d+\s+\d+ • .*|\d+\.\d+ • .*\s+\d+|PYTHON CODE)$")

VISION_PROMPT = """You are indexing one figure from a data science textbook so that a search engine can find it \
and a reader can answer questions from your description. Caption: {caption!r}. Text near the figure: {near!r}.
Describe ONLY what is visible:
1. Type (line chart, bar chart, histogram, scatterplot, heatmap, map, diagram/flowchart, screenshot, photo, ...).
2. Title, axis labels with units, axis ranges and tick values, legend entries / series names and colors.
3. Every number or label printed in the figure.
4. For charts: key values you can read off the axes (say "approximately" when reading between ticks), highest / \
lowest points, trends, and how series compare. For histograms and bar charts, list EVERY bar as its bin interval \
or category followed by its value, e.g. "67.95-69.95: 0.17" (never label a bar by a single edge value). \
For diagrams: every node, arrow and step in order.
Never invent values. If something cannot be read, say "not readable". Plain text, no markdown headers."""
VISION_PROMPT_VERSION = 2  # v2 added the bar/histogram rule; v1 descriptions of non-bar figures are kept (cached)

TABLE_PROMPT = """This image is a table from a data science textbook. Caption: {caption!r}. {near}
Transcribe the table exactly as a Markdown table: every row, column header and cell, including numbers and \
formulas (write math in plain text, e.g. x_hat_2 = 0.75*x_1 + 0.25*x_hat_1 = 1848.36, or (1/512)*2043.94 = 3.99). \
Do not add, explain or compute anything."""
MATH_PROMPT = """This image is one paragraph from a data science textbook. Transcribe it exactly. Math symbols and \
formulas are drawn as images: write them in plain text (e.g. d = 2, q = 0, x_hat_t, p-value of 7.852 x 10^-14, \
ARIMA(12, 2, 0)). Do not add, explain or compute anything."""
# genuine transcriptions add only math words (hat, alpha, sum, epsilon, logit: 0-4 on this book); 11+ = invented text
MATH_MAX_ADDED = 6
SPARSE = 0.15  # tables with more empty cells than this lost math cells in the PDF text layer -> transcribe image


def sections_by_page(doc) -> dict[int, list[str]]:
    starts = [(p, t.split()[0]) for lvl, t, p in doc.get_toc() if lvl == 2 and re.match(r"\d+\.\d+ ", t)]
    out = {}
    for pno in range(1, doc.page_count + 1):
        cur = [s for p, s in starts if p <= pno]
        out[pno] = cur[-1:] + [s for p, s in starts if p == pno and s not in cur[-1:]]
    return out


def fallback_caption(blocks, rect, pno: int) -> str:
    """For figures without a printed caption (mostly Python output): the text just before and after the figure,
    so search can find it by what the book says about it. Marked as page text, not a caption."""
    before = " ".join(" ".join(b[4].split()) for b in blocks if b[3] <= rect.y0 + 2)[-200:]
    after = " ".join(" ".join(b[4].split()) for b in blocks if b[1] >= rect.y1 - 2)[:250]
    return f"Figure on page {pno} (no printed caption). Text before it: ...{before} Text after it: {after}..."


def caption_near(blocks, rect, word: str) -> str:
    """Closest text block that starts with 'Figure x.y'/'Table x.y', below (or else above) the region."""
    cands = [b for b in blocks if b[4].strip().startswith(word)]
    if not cands:
        return ""
    best = min(cands, key=lambda b: (0 if b[1] >= rect.y1 - 2 else 1, abs(b[1] - rect.y1)))
    return " ".join(best[4].split())


def describe(png: bytes, caption: str, near: str, key: str, prompt: str = "", version: str = "table-v1") -> dict:
    body = {"model": VISION_MODEL, "temperature": 0.01, "messages": [{"role": "user", "content": [
        {"type": "text", "text": prompt or VISION_PROMPT.format(caption=caption, near=near[:600])},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode(),
                                            "detail": "high"}}]}]}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                                          "Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"vision failed for {key}: HTTP {e.code} {e.read()[:300]!r}") from None
    u = resp["usage"]
    return {"description": resp["choices"][0]["message"]["content"], "model": VISION_MODEL,
            "prompt_version": VISION_PROMPT_VERSION if not prompt else version,
            "prompt_tokens": u["prompt_tokens"], "completion_tokens": u["completion_tokens"],
            "cost_usd": (u["prompt_tokens"] * PRICE[0] + u["completion_tokens"] * PRICE[1]) / 1e6,
            "latency_s": round(time.perf_counter() - t0, 1)}


def fix_math(page, pno, body, cache, cache_path, failures) -> tuple[list, set]:
    """Math in this PDF is drawn as small vector shapes, so the text layer has gaps ('positive values of  did not
    change'). Blocks containing such shapes are re-read from the page image (cached, like sparse tables)."""
    glyphs = [pymupdf.Rect(d["rect"]) for d in page.get_drawings() if d["rect"].width < 60 and d["rect"].height < 25]
    out, fixed = [], set()
    for k, b in enumerate(body):
        r = pymupdf.Rect(b[:4])
        key = f"p{pno}_m{k}"
        if any(r.intersects(g) for g in glyphs):
            if key not in cache:
                try:
                    png = page.get_pixmap(clip=r + (-2, -2, 2, 2), dpi=200).tobytes("png")
                    cache[key] = describe(png, "", "", key, MATH_PROMPT, "math-v1")
                    cache_path.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
                except Exception as e:  # logged; the block keeps its (gappy) text layer
                    failures.append({"page": pno, "math_block": key, "error": str(e)})
            if key in cache:
                new = cache[key]["description"]
                words = lambda t: re.findall(r"[A-Za-z]{3,}", t.lower())  # noqa: E731
                added = [w for w in words(new) if w not in set(words(b[4]))]
                if len(added) > MATH_MAX_ADDED:  # tiny blocks get "continued" by the model with invented text
                    failures.append({"page": pno, "math_block": key, "error": f"transcription rejected: adds "
                                     f"{len(added)} words not in the text layer (e.g. {added[:5]}); text layer kept"})
                else:
                    b = (*b[:4], new, *b[5:])
                    fixed.add(" ".join(new.split()))
        out.append(b)
    return out, fixed


def text_chunks(blocks, pno, chapter, sections) -> list[dict]:
    chunks, buf = [], []
    for b in blocks + [None]:
        t = None if b is None else " ".join(b[4].split())
        if b is None or (buf and len(" ".join(buf)) + len(t) > MAX_CHARS):
            if buf:
                chunks.append(" ".join(buf))
            buf = []
        if t:
            buf.append(t)
    return [{"id": f"ADV:p{pno}:t{i}", "text": c, "source_id": SOURCE_ID, "source": SOURCE, "page": pno,
             "metadata": {"chapter": chapter, "sections": sections, "type": "text"}} for i, c in enumerate(chunks)]


def extract() -> None:
    doc = pymupdf.open(PDF)
    secs = sections_by_page(doc)
    (OUT / "crops").mkdir(parents=True, exist_ok=True)
    cache_path = OUT / "figures.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    chunks, excluded, failures, per_type = [], [], [], {"text": 0, "table": 0, "figure": 0}
    for chapter, (first, last, end) in CHAPTERS.items():
        excluded += [{"page": p, "chapter": chapter, "reason": "end-of-chapter material (Key Terms onward)"}
                     for p in range(last + 1, end + 1)]
        for pno in range(first, last + 1):
            page = doc[pno - 1]
            blocks = [b for b in page.get_text("blocks", sort=True) if b[6] == 0 and b[4].strip()
                      and not NOISE.match(" ".join(b[4].split()))]
            tables = page.find_tables().tables
            figs = [pymupdf.Rect(i["bbox"]) for i in page.get_image_info()
                    if i["bbox"][2] - i["bbox"][0] >= MIN_FIG and i["bbox"][3] - i["bbox"][1] >= MIN_FIG]
            regions = [pymupdf.Rect(t.bbox) for t in tables] + figs
            # text = blocks outside table/figure regions (table text is kept as a structured table chunk instead)
            body = [b for b in blocks if not any(pymupdf.Rect(b[:4]).intersects(r) for r in regions)]
            for k, t in enumerate(tables):
                md = t.to_markdown().strip()
                cap = caption_near(blocks, pymupdf.Rect(t.bbox), "Table")
                # the cell parser can drop characters ("Is a fower" on p300); keep the region's raw text as well
                raw = " ".join(page.get_text("text", clip=pymupdf.Rect(t.bbox)).split())
                body_md = f"{cap}\n{md}\nRaw text of table region: {raw}".strip()
                cells = [x.strip() for line in md.splitlines() if line.startswith("|") and not line.startswith("|---")
                         for x in line[1:-1].split("|")]
                transcribed = None
                if cells and sum(x in ("", "<br>") for x in cells) / len(cells) > SPARSE:
                    key = f"p{pno}_tab{k}"
                    if key not in cache:
                        try:
                            png = page.get_pixmap(clip=pymupdf.Rect(t.bbox), dpi=200).tobytes("png")
                            (OUT / "crops" / f"{key}.png").write_bytes(png)
                            cache[key] = describe(png, cap, "", key, TABLE_PROMPT.format(caption=cap, near=""))
                            cache_path.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
                        except Exception as e:
                            failures.append({"page": pno, "table": key, "error": str(e)})
                    if key in cache:
                        transcribed = cache[key]["model"]
                        body_md += (f"\n[Cells missing from the PDF text layer (math). Table transcribed from the page "
                                    f"image by {transcribed}]\n{cache[key]['description']}")
                chunks.append({"id": f"ADV:p{pno}:tab{k}", "text": body_md,
                               "source_id": SOURCE_ID,
                               "source": SOURCE, "page": pno,
                               "metadata": {"chapter": chapter, "sections": secs[pno], "type": "table",
                                            "caption": cap, "bbox": [round(x, 1) for x in t.bbox],
                                            "rows": t.row_count, "cols": t.col_count,
                                            "transcribed_by": transcribed}})
                per_type["table"] += 1
            for k, r in enumerate(figs):
                key = f"p{pno}_fig{k}"
                crop = OUT / "crops" / f"{key}.png"
                png = page.get_pixmap(clip=r, dpi=200).tobytes("png")
                crop.write_bytes(png)
                cap = caption_near(blocks, r, "Figure") or fallback_caption(blocks, r, pno)
                near = " ".join(" ".join(b[4].split()) for b in body)[:600]
                if key not in cache:
                    try:
                        cache[key] = describe(png, cap, near, key)
                        cache_path.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
                    except Exception as e:  # logged, never replaced with a fake description
                        failures.append({"page": pno, "figure": key, "error": str(e)})
                        continue
                d = cache[key]
                chunks.append({"id": f"ADV:p{pno}:fig{k}",
                               "text": f"{cap}\n[Figure description generated by {d['model']}]\n{d['description']}".strip(),
                               "source_id": SOURCE_ID, "source": SOURCE, "page": pno,
                               "metadata": {"chapter": chapter, "sections": secs[pno], "type": "figure",
                                            "caption": cap, "bbox": [round(x, 1) for x in r],
                                            "crop": str(crop.relative_to(ROOT)), "generated_by": d["model"]}})
                per_type["figure"] += 1
            body, fixed = fix_math(page, pno, body, cache, cache_path, failures)
            tc = text_chunks(body, pno, chapter, secs[pno])
            for c in tc:
                if any(f in c["text"] for f in fixed):
                    c["metadata"]["math_transcribed_by"] = VISION_MODEL
            chunks += tc
            per_type["text"] += len(tc)
            if not (body or tables or figs):
                failures.append({"page": pno, "error": "no content extracted"})
        print(f"chapter {chapter}: done", flush=True)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids)), "duplicate chunk id"
    (OUT / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1) + "\n")
    report = {"pdf": SOURCE, "chapters": {c: {"content_pages": [a, b], "chapter_pages": [a, e]}
                                          for c, (a, b, e) in CHAPTERS.items()},
              "content_pages": sum(b - a + 1 for a, b, _ in CHAPTERS.values()),
              "document_pages": sum(e - a + 1 for a, _, e in CHAPTERS.values()),
              "chunks": len(chunks), "by_type": per_type, "excluded_pages": excluded, "failures": failures,
              "vision_calls": len(cache), "vision_cost_usd": round(sum(float(v["cost_usd"]) for v in cache.values()), 4),
              "math_blocks_transcribed": sum(k.split("_")[1].startswith("m") for k in cache),
              "min_figure_size_pt": MIN_FIG, "text_chunk_max_chars": MAX_CHARS}
    (OUT / "index_report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "excluded_pages"}, indent=1))


# OCR variant: figures read by Tesseract; the cached vision description is used only where OCR failed.
# Thresholds set on dev crops (p430, p436, p454 fail; p447, p317, p242, p234 pass). Tables/text are unchanged.
OCR_MIN_CONF, OCR_MIN_WORDS, OCR_GOOD = 70, 10, 60


def tesseract(png) -> tuple[str, float, int]:
    """Printed text of a crop (words with confidence >= OCR_GOOD, grouped by line), mean confidence, good-word count."""
    tsv = subprocess.run(["tesseract", str(png), "-", "--psm", "11", "tsv"], capture_output=True, text=True,
                         check=True).stdout.splitlines()
    rows = [r.split("\t") for r in tsv[1:]]
    words = [r for r in rows if len(r) == 12 and r[11].strip() and float(r[10]) >= 0]
    good = [r for r in words if float(r[10]) >= OCR_GOOD]
    lines: dict[tuple, list[str]] = {}
    for r in good:
        lines.setdefault((int(r[2]), int(r[3]), int(r[4])), []).append(r[11])
    mean = sum(float(r[10]) for r in words) / len(words) if words else 0.0
    return "\n".join(" ".join(w) for w in lines.values()), mean, len(good)


def ocr() -> None:
    version = subprocess.run(["tesseract", "--version"], capture_output=True, text=True).stdout.split()[1]
    chunks, report = json.loads((OUT / "chunks.json").read_text()), []
    for c in chunks:
        if c["metadata"]["type"] != "figure":
            continue
        text, mean, n = tesseract(ROOT / c["metadata"]["crop"])
        failed = mean < OCR_MIN_CONF or n < OCR_MIN_WORDS
        report.append({"id": c["id"], "mean_conf": round(mean, 1), "good_words": n,
                       "used": "vision (OCR failed)" if failed else "tesseract"})
        if not failed:
            cap = c["metadata"]["caption"]
            c["text"] = f"{cap}\n[Printed text read by Tesseract {version} OCR: labels and numbers only, no layout]\n{text}".strip()
            c["metadata"] = {**c["metadata"], "generated_by": f"tesseract {version}", "ocr_mean_conf": round(mean, 1)}
    (OUT / "chunks_ocr.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1) + "\n")
    used = sum(r["used"] == "tesseract" for r in report)
    (OUT / "ocr_report.json").write_text(json.dumps(
        {"tesseract": version, "psm": 11, "min_mean_conf": OCR_MIN_CONF, "min_good_words": OCR_MIN_WORDS,
         "good_word_conf": OCR_GOOD, "figures": len(report), "tesseract_used": used,
         "vision_fallback": len(report) - used, "per_figure": report}, indent=1) + "\n")
    print({"figures": len(report), "tesseract_used": used, "vision_fallback": len(report) - used})


def embed(file: str = "chunks.json", strategy: str = "ADV") -> None:
    from day6.embeddings import OpenAIEmbedder
    from day6.models import Chunk
    from day6.store import PgVectorStore, content_hash
    chunks = json.loads((OUT / file).read_text())
    emb = OpenAIEmbedder("text-embedding-3-small")
    store = PgVectorStore(os.environ["DATABASE_URL"], emb.dimensions)
    have = store.existing_hashes(strategy)
    todo = [c for c in chunks if have.get(c["id"]) != content_hash(c["text"])]
    objs = [Chunk(c["id"], c["source_id"], c["source"], c["page"], c["text"], c["metadata"]) for c in todo]
    if objs:
        store.upsert(strategy, objs, emb.embed_documents([c.text for c in objs]))
    removed = store.delete_obsolete(strategy, SOURCE_ID, {c["id"] for c in chunks})
    rows, distinct = store.count(strategy)
    print({"embedded": len(objs), "removed": removed, "rows": rows, "distinct": distinct,
           "tokens": emb.tokens_used, "cost_usd": round(emb.cost_usd, 6)})


if __name__ == "__main__":
    {"extract": extract, "embed": embed, "ocr": ocr}[sys.argv[1]](*sys.argv[2:])
