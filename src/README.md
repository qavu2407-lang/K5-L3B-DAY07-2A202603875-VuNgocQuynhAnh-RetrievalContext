# Code và cách chạy

Agent tìm bằng chứng trong giáo trình *Principles of Data Science* (chương 1-3; chương 5, 6, 9 cho thử thách nâng cao), trả lời có trích nguồn hoặc từ chối khi không đủ bằng chứng. Dùng lại vector store và embedding của Day 6.

## Cần có

- Python 3.11, Docker, OpenAI API key.
- Repo Day 6 đã chạy xong (có database pgvector): https://github.com/qavu2407-lang/K5-L3B-DAY06-2A202603875-DataIngestion (commit `0581c6e`).

## Cài đặt

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Tạo file `.env` ở thư mục gốc (không commit file này):

```
OPENAI_API_KEY=...
DATABASE_URL=postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab
DAY6_DIR=/đường/dẫn/tới/repo/Day6
```

Bật database của Day 6 (chạy trong thư mục `starter/` của repo Day 6):

```bash
docker compose -p day6_student_starter up -d --wait
```

## Chạy theo thứ tự

| Bước | Lệnh | Kết quả |
|---|---|---|
| 1. Xuất dữ liệu Day 6 | `.venv/bin/python src/export_day6.py` | `data/day6/chunks.json` (524), `questions.json` (24) |
| 2. Kiểm tra benchmark | `.venv/bin/python src/check_benchmark.py` | số câu đủ, gold hợp lệ, câu thiếu evidence không có từ khóa |
| 3. Kiểm tra kết nối | `.venv/bin/python src/check_connection.py` | top-3 trùng Day 6 20/20 |
| 4. So sánh retrieval (dev) | `.venv/bin/python src/retrieval.py --method dense\|lexical\|hybrid --split dev`, rồi `src/compare.py dev dense lexical hybrid` | `results/dev-<method>/`, `results/dev_comparison.md` |
| 5. Agent (dev) | `.venv/bin/python src/agent.py --retriever hybrid --distinct-queries --budget 9600 --skip-seen --split dev --name I3` | `results/agent-dev-I3/` |
| 6. So sánh agent | `.venv/bin/python src/agent_compare.py dev A0 A1 I1 I2 I3` | `results/agent_dev_comparison.md` |
| 7. Test (sau khi chốt) | lệnh trong `results/frozen_config.json` (cần `--confirm-frozen`) | `results/agent-test-<config>/` |
| 8. Tổng hợp nhãn | `.venv/bin/python starter/agent_metrics.py --cases data/day6/questions.json --traces results/agent-test-I3/traces.json --reviews results/agent-test-I3/reviews.json --split test --output results/agent-test-I3/metrics.json` | `metrics.json` |

Kiểm tra code (không cần mạng): `.venv/bin/python -m unittest discover -s tests`.

## Các cấu hình agent

| Tên | Lệnh thêm | Ý nghĩa |
|---|---|---|
| A0 | `--retriever dense` | baseline |
| A1 | `--retriever hybrid` | dense + TF-IDF (RRF) |
| I1 | A1 + `--distinct-queries` | không cho lặp lại query |
| I2 | I1 + `--budget 9600` | context lớn hơn cho nhiều lượt tìm |
| I3 (đã chọn) | I2 + `--skip-seen` | lượt tìm sau bỏ qua chunk đã thấy |

## Thử thách nâng cao (chương 5, 6, 9)

Cần PDF của Day 6 (`$DAY6_DIR/data/Principles-of-Data-Science-WEB.pdf`). Mô tả hình và đoạn công thức đã lưu sẵn trong `data/advanced/figures.json`, nên chạy lại `extract` không gọi model.

| Bước | Lệnh | Kết quả |
|---|---|---|
| 1. Trích text, bảng, hình | `.venv/bin/python src/adv_index.py extract` | `data/advanced/chunks.json`, `index_report.json`, `crops/` |
| 2. Embed vào pgvector | `.venv/bin/python src/adv_index.py embed` | strategy `ADV` trong database Day 6 |
| 3. Kiểm tra benchmark | `.venv/bin/python src/adv_check.py` | đủ số câu theo nhóm, evidence trỏ đúng trang |
| 4. Agent (dev) | `.venv/bin/python src/agent.py --corpus advanced --split dev --retriever hybrid --budget 9600 --distinct-queries --skip-seen --typed-search --calculator --verify --append-citations --read-figure --figure-nudge --prompt v7 --neighbours --verify-model gpt-6.1-terra --name F6` | `results/adv-agent-dev-F6/` |
| 5. Test (sau khi chốt) | lệnh trong `results/adv_frozen_config.json` (cần `--confirm-frozen`) | `results/adv-agent-test-F6/` |

Các cấu hình dev và thay đổi từng bước: `results/adv_dev_comparison.md`.

## File

| File | Công dụng |
|---|---|
| `day6_store.py` | Import embedder và store của Day 6, trả chunk theo định dạng Day 7 |
| `export_day6.py` | Xuất chunk + câu hỏi Day 6, gộp câu thiếu evidence (`data/unanswerable.json`) |
| `check_benchmark.py`, `check_connection.py` | Kiểm tra benchmark và kết nối |
| `retrieval.py` | 3 phương pháp (dense, TF-IDF, hybrid) và chấm Hit@1 / Hit@3 / Context Evidence Rate |
| `agent.py` | Agent `gpt-4.1-mini` dùng `run_agent` của starter |
| `adv_index.py`, `adv_check.py` | Index tài liệu nâng cao (text, bảng, hình) và kiểm tra benchmark nâng cao |
| `compare.py`, `agent_compare.py` | Bảng so sánh |

## Demo (đã có sẵn trong `results/`)

- **Trả lời có bằng chứng:** I3, câu t04 — "sample space" [p130:0] (`results/agent-test-I3/traces.json`).
- **Từ chối đúng:** I3, câu t06 (web scraping có hợp pháp không) — sách không nói, agent từ chối.
- **Lỗi:** A0, câu t04 — trả lời đúng nhưng trích chunk không chứa định nghĩa (chunk đúng không vào context).

Nguồn sách: *Principles of Data Science*, OpenStax, Rice University, CC BY-NC-SA 4.0. Access for free at openstax.org.
