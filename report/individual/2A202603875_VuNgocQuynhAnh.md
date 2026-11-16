# Báo cáo Day 7

## Dữ liệu và benchmark

- Nguồn, quyền sử dụng, số trang và số chunk: giáo trình OpenStax *Principles of Data Science* (2025, PDF 569 trang), giấy phép CC BY-NC-SA 4.0. Chỉ dùng chương 1-3: **116 trang nội dung, 524 chunk** (cấu hình B của Day 6: chunk theo đoạn, tối đa 1.000 ký tự, không vượt qua trang). PDF không có trong repo; tải tại openstax.org và kiểm tra bằng sha256 trong `data/manifest.json` của repo Day 6.
- Vector store, embedding model, phiên bản và số chiều: dùng lại nguyên Day 6. PostgreSQL 16.16 + pgvector 0.8.7 (Docker), tìm cosine chính xác (không dùng index ANN). Embedding OpenAI `text-embedding-3-small`, **1536 chiều**; câu hỏi và chunk dùng cùng model. Code Day 7 import trực tiếp class của Day 6 (repo Day 6, commit `0581c6e`). Kiểm tra kết nối: top-3 của Day 7 trùng Day 6 ở **20/20 câu** (`results/connection_check.json`).
- Agent model, cách chạy và phân chia dev/test: agent dùng OpenAI **`gpt-4.1-mini`**, temperature 0,01, gọi tool qua function calling. Cách chạy: `src/README.md`. Chia dev/test: giữ split của Day 6 (15 dev / 5 test câu có đáp án) và thêm 2 + 2 câu thiếu evidence. Chỉ thử và chọn cấu hình trên dev; test chạy **một lần** cho mỗi cấu hình sau khi chốt.
- Cách xác định câu có/thiếu evidence và tiêu chí chấm: 24 câu trong `data/day6/questions.json` (tạo bằng `src/export_day6.py`). **Dev 15 có đáp án + 2 thiếu evidence; test 5 + 2.** 20 câu có đáp án lấy nguyên từ Day 6 (giữ split cũ), mỗi câu có `gold` = nguồn, trang và câu evidence nằm trọn trong một chunk; d15 chấp nhận trang 29 hoặc 30. 4 câu thiếu evidence viết mới trong `data/unanswerable.json`, gần chủ đề của sách: d16 (giá Colab Pro, gần §1.5), d17 (cỡ mẫu cho sai số 5%, gần §2.2), t06 (web scraping có hợp pháp không, robots.txt, gần §2.3), t07 (phân phối siêu bội, gần §3.5). Cách kiểm tra thiếu evidence: (1) `src/check_benchmark.py` khẳng định các từ khóa trong `absence_checks` có 0 kết quả trong 524 chunk của khoảng trang tương ứng; (2) tìm trên toàn bộ PDF 569 trang; (3) đọc trực tiếp PDF trang 76-86 (t06) và 139-146 (t07), vì ký hiệu toán bị mất khi trích text; (4) xem top-3 dense để chắc câu hỏi gần chủ đề (chỉ kiểm tra, không dùng để chỉnh). "Thiếu" nghĩa là thiếu trong chương 1-3 đã index: d17 có nội dung liên quan ở chương 4 (trang 157-168), không được index. Tiêu chí chấm theo BENCHMARK.md: câu có đáp án chấm 0/1/2, từ chối = 0; câu thiếu evidence đạt khi agent từ chối hoặc nói rõ không đủ bằng chứng, không khẳng định thêm (với d16, nói "sách chỉ ghi Colab miễn phí" vẫn tính là từ chối đúng). Câu thiếu evidence không tính vào mẫu số retrieval metrics. **Hạn chế:** kết quả test Day 6 (t01-t05) đã được xem ở Day 6 (không dùng để chỉnh); t02 cùng mục 2.2 với d10, t05 cùng mục 2.4 với d11-d14. Gold không bao giờ được đưa vào agent hay retrieval.

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline | Dense: OpenAI `text-embedding-3-small` + pgvector cosine chính xác (Day 6 B), top-3, filter `chapter` khi câu hỏi có, không rerank, budget 3.200 ký tự | Tái lập Day 6 cấu hình C (khớp 7/15, 12/15) | dev | 7/15 (46,7%) | 12/15 (80,0%) | 12/15 (80,0%) | trung vị 634 ms/câu, 11,9 s tổng; 236 token = $0,000005 |
| Phương pháp 2 | Lexical: TF-IDF của starter (`\w+`, chữ thường), top-3, cùng filter (lọc sau khi chấm điểm), không rerank, 3.200 ký tự | Khớp đúng thuật ngữ trong sách (vd. "sample space") mà embedding bỏ lỡ | dev | 7/15 (46,7%) | 12/15 (80,0%) | 12/15 (80,0%) | trung vị 3 ms/câu, 0,05 s; $0 |
| Phương pháp 3 | Hybrid: RRF (k=60) của dense top-20 + TF-IDF top-20, top-3, cùng filter, không rerank, 3.200 ký tự | Hai phương pháp sai ở câu khác nhau, nên gộp thứ hạng sẽ bù cho nhau | dev | 8/15 (53,3%) | 13/15 (86,7%) | 13/15 (86,7%) | trung vị 501 ms/câu, 9,5 s; 236 token = $0,000005 |
| Agent A0 (baseline agent) | Agent `gpt-4.1-mini` + dense, top-3, tối đa 3 lượt tìm, 3.200 ký tự | Baseline cho phần agent | dev | 7/15 | 12/15 | 11/15 (context cuối của agent) | trung vị 5,1 s/câu; $0,019 cho 17 câu |
| Agent A1 | Agent + hybrid, còn lại như A0 | Retrieval tốt hơn (phương pháp 3) giúp câu trả lời tốt hơn | dev | 8/15 | 13/15 | 14/15 | 3,7 s/câu; $0,018 |
| Cải thiện 1 (I1) | A1 + bắt buộc query khác nhau: query trùng bị trả lại một lần (có log) để viết lại | Agent lặp lại đúng một query (A0: 15 lần, A1: 9 lần) nên các lượt tìm sau vô ích | dev | 8/15 | 13/15 | 14/15 | 4,0 s/câu; $0,019 |
| Cải thiện 2 (I2) | I1 + budget 9.600 ký tự (3 lượt × 3.200) | Context gần đầy sau lượt 1, nên chunk mới từ lượt 2-3 không vào được | dev | 8/15 | 13/15 | 14/15 | 3,9 s/câu; $0,019 |
| Cải thiện 3 (I3) | I2 + lượt tìm sau bỏ qua chunk đã thấy (trả về chunk tốt nhất chưa thấy) | Top-3 "bão hòa": mọi cách viết query đều trả về cùng 3 chunk Colab, chunk gold d07 nằm hạng 4-9 | dev | 8/15 | 13/15 | **15/15** | 3,9 s/câu; $0,022 |
| Cấu hình đã chọn (I3) | Agent + hybrid, top-3, tối đa 3 lượt, query khác nhau, bỏ chunk đã thấy, 9.600 ký tự | Đã chốt trên dev (`results/frozen_config.json`) | test | 4/5 (80%) | 5/5 (100%) | retrieval: 5/5; context cuối của agent: 5/5 | trung vị 4,4 s/câu; $0,0097 cho 7 câu |
| Baseline (A0) | Agent + dense, top-3, tối đa 3 lượt, 3.200 ký tự | Baseline | test | 4/5 (80%) | 4/5 (80%) | retrieval: 4/5; context cuối của agent: 4/5 | trung vị 5,3 s/câu; $0,0084 cho 7 câu |

Một cấu hình có thể đồng thời là phương pháp mới và cải thiện; giải thích rõ. Báo `n/N` và tỷ lệ, ghi đơn vị thời gian/chi phí, so sánh test sau khi chốt. Nêu hai lỗi dev, nguyên nhân, cách thử và lý do chọn cấu hình:

**Điều kiện so sánh 3 phương pháp:** cùng corpus (Day 6 strategy B, 524 chunk), cùng 17 câu dev (15 có đáp án, N = 15; d16, d17 thiếu evidence nên không tính vào mẫu số), cùng nhãn gold, cùng query gốc (không viết lại), cùng filter (chỉ dùng `chapter` khi câu hỏi có sẵn: d13, d14, d15). Hit = chunk đúng nguồn, đúng trang và chứa trọn câu evidence (`baseline.hit`). Context = top-3 được đóng gói bằng `pack_context` của starter. Lệnh chạy: `.venv/bin/python src/retrieval.py --method dense|lexical|hybrid --split dev`; trace ở `results/dev-<method>/traces.json` (top-10, score, rank, hit, context), bảng theo từng câu ở `results/dev_comparison.md`. MRR@10: dense 0,649, lexical 0,643, hybrid 0,715.

**Vì sao context budget là 3.200 ký tự thay vì 800 của starter:**
- Chunk Day 6 (strategy B) dài: trung vị 476 ký tự, p90 914, tối đa 999; mỗi khối còn có thêm header nguồn tới 82 ký tự. **143/524 chunk (27%) không vừa 800 ký tự ngay cả khi đứng một mình**, nên với budget 800, evidence nằm trong các chunk này không bao giờ vào được context, dù retrieval đã tìm đúng.
- Đo trực tiếp trên dev, cùng top-3: Context Evidence Rate ở budget 800 chỉ còn dense 5/15, lexical 4/15, hybrid 6/15, so với 12/15, 12/15, 13/15 ở 3.200. Như vậy budget 800 làm mất hơn nửa số evidence đã tìm được, và chỉ số context lúc đó đo budget chứ không đo retrieval.
- 3.200 ký tự (khoảng 800 token) vừa với 3 chunk trong gần như mọi trường hợp: trường hợp xấu nhất (3 chunk dài tối đa + header) là 3.247 ký tự. Trên dev không câu nào bị bỏ chunk (`questions_with_dropped_chunks` = 0); trace ghi lại nếu có. Context trung bình thực tế khoảng 2.000 ký tự.
- Chi phí: khoảng 800 token context mỗi câu là nhỏ với model agent; budget lớn hơn chỉ thêm chunk xếp hạng thấp. Các cách chọn context khác (dedup, chunk lân cận, nén, nhiều lượt tìm) sẽ thử riêng ở phần agent.
- Hệ quả cần lưu ý: với một lượt tìm và budget này, Context Evidence Rate bằng Evidence Hit@3. Hai chỉ số chỉ khác nhau khi agent tìm nhiều lượt hoặc khi thay đổi cách chọn context.

**Ghi chú về bảng:** với các dòng agent, Hit@1 và Evidence Hit@3 là của retrieval trên **query gốc** (giống dòng phương pháp tương ứng, vì agent dùng cùng retriever). Context Evidence Rate là của **context cuối mà agent gửi model** (gộp nhiều lượt tìm, nên có thể cao hơn Hit@3). Agent tự viết lại query; mọi query của agent được lưu trong `results/agent-dev-<config>/traces.json`. Bảng đầy đủ: `results/agent_dev_comparison.md` (tạo bằng `src/agent_compare.py`).

**Kết quả câu trả lời trên dev (nhãn thủ công, quy tắc trong `reviews.json`):**

| Cấu hình | Grounded 0/1/2 | Trung bình /2 | Citation hợp lệ | Từ chối đúng | Từ chối nhầm | Query lặp | Chunk mới từ lượt sau |
|---|---|---|---|---|---|---|---|
| A0 | 2/3/10 | 1,53 | 22/24 | 2/2 | 1/15 | 15 | 1 |
| A1 | 0/1/14 | 1,93 | 24/24 | 2/2 | 0/15 | 9 | 2 |
| I1 | 0/1/14 | 1,93 | 21/22 | 2/2 | 0/15 | 0 | 3 |
| I2 | 0/1/14 | 1,93 | 24/24 | 2/2 | 0/15 | 0 | 5 |
| I3 | 0/1/14 | 1,93 | 26/26 | 2/2 | 0/15 | 0 | 30 |

**Lỗi dev 1 — d07: chunk gold không bao giờ vào context (A0, A1, I1, I2).**
- *Hiện tượng:* câu hỏi "nên làm gì sau khi sửa code ở nhiều cell Colab?". Đáp án nằm ở p45:0 ("nên dùng 'Run all' hoặc 'Run before'"). A0 trả lời chung chung "chạy theo thứ tự từ trên xuống" (điểm 1); A1/I1/I2 nói "Run all" nhưng dựa vào p43:0, chunk chỉ giải thích Run all làm gì.
- *Nguyên nhân (đo được):* với cả 3 query mà agent đã gửi, ba chunk p42:0, p43:0, p43:1 luôn chiếm top-3 ở cả dense, lexical và hybrid; p45:0 chỉ đứng hạng 4-9. p45:0 bắt đầu giữa một ví dụ code từ trang 44 (lỗi chunk dừng ở cuối trang đã ghi ở Day 6), nên ít giống query.
- *Thử:* I1 (query khác nhau) — agent viết lại query nhưng top-3 không đổi. I2 (budget lớn hơn) — có chỗ trống nhưng không có chunk mới để thêm. I3 (lượt tìm sau bỏ qua chunk đã thấy) — lượt 2 trả về p45:0, agent trả lời đúng nguyên văn "Run all" hoặc "Run before" và trích p45:0.
- *Trước/sau:* Context Evidence Rate của agent 14/15 → 15/15; chunk mới từ các lượt sau 5 → 30. Điểm trung bình không đổi (1,93) vì A1 d07 đã được chấm 2 theo quyết định của người chấm (câu trả lời đúng, p43:0 hỗ trợ hành động), nên lợi ích của I3 ở d07 là bằng chứng đúng chứ không phải điểm.

**Lỗi dev 2 — agent lặp lại đúng một query, lượt tìm sau vô ích (A0 d07, d10, d14; A1 d07, d14).**
- *Hiện tượng:* A0 gửi cùng một query 3 lần ở 6 câu (15 lần lặp). Ở d14, cả 3 lượt trả về cùng 3 chunk không có p88:2 nên agent từ chối nhầm; ở d10, agent không thấy chunk về stratified sampling và trả lời mâu thuẫn (kết luận quota sampling, điểm 0).
- *Nguyên nhân:* model coi việc tìm lại là cách "chắc chắn hơn", nhưng retrieval là xác định nên cùng query luôn trả cùng kết quả; cộng thêm `pack_context` của starter giữ chunk cũ trước nên context hầu như không đổi (A0: cả 9 câu tìm nhiều lần chỉ thêm 1 chunk mới).
- *Thử:* A1 (hybrid) đưa p88:2 và p76:1 vào top-3 ngay lượt đầu nên d10, d14 được sửa (điểm 0 → 2). I1 loại bỏ hoàn toàn query lặp (9 → 0) nhưng chỉ thêm được 1 chunk mới, vì các query viết lại vẫn trả về cùng top-3 (xem lỗi 1). Kết hợp với I3 thì các lượt sau mới thật sự mang thêm bằng chứng.

**Lỗi chưa sửa — d12: câu trả lời thêm khẳng định không có căn cứ (mọi cấu hình).** Mọi cấu hình đều thêm "giảm cỡ mẫu và gây bias" khi nói về việc xóa dữ liệu thiếu; sách (p86:3) nói điều này về bản thân dữ liệu thiếu, không phải về việc xóa. Đây là lỗi sinh câu trả lời, không phải retrieval; không thử sửa trong bài này. Chấm 1 theo quy tắc chặt.

**Chọn cấu hình (theo tiêu chí viết trước, `results/selection_criteria.md`):** mọi cấu hình đều đủ điều kiện (0 lỗi, từ chối đúng 2/2). Tiêu chí chính: A1, I1, I2, I3 hòa (1,93; chênh < 0,10), đều hơn A0 0,40. Phá hòa 1 (từ chối nhầm): hòa (0/15). Phá hòa 2 (citation hợp lệ): I1 bị loại (21/22). Phá hòa 3 (Context Evidence Rate của agent): **I3 15/15** so với 14/15 → **chọn I3**. Đánh đổi: I3 tốn hơn A1 22% ($0,00127 so với $0,00104 mỗi câu), thời gian như nhau. I3 được thêm sau khi xem kết quả I1/I2 trên dev (ghi trong phụ lục của file tiêu chí); tiêu chí không đổi. Cấu hình chốt: `results/frozen_config.json`. Chưa chạy test.

**Nhận xét ban đầu về retrieval trên dev:** dense và lexical bằng điểm nhưng sai ở câu khác nhau. Lexical tốt hơn ở d01 (hạng 3 so với 5), d12 và d14 (hạng 2 so với 4); dense tốt hơn ở d06 (2 so với 8) và d10 (2 so với 4). Hybrid đưa d10 lên hạng 1 và d14 lên hạng 2, nhưng d06 rơi xuống hạng 4. **d07 sai ở cả ba** (hạng 8/10/7): lỗi chunk dừng ở cuối trang đã ghi ở Day 6, retrieval không sửa được. Với hai câu thiếu evidence, top-1 của mọi phương pháp vẫn là chunk gần chủ đề (p41 Colab cho d16), nên agent phải tự nhận ra là không đủ bằng chứng.

## Agent và đánh giá

- Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi: model `gpt-4.1-mini` (OpenAI, temperature 0,01) điều phối qua function calling với 3 tool: `search(query)`, `answer(answer, citations)`, `abstain(reason)`; `tool_choice="required"`, một tool mỗi lượt. Vòng lặp, đóng gói context và kiểm tra citation dùng `run_agent` của starter (`src/agent.py`). **Điều kiện dừng:** tối đa 3 lượt tìm; khi hết lượt chỉ còn `answer`/`abstain` (model không thể vượt giới hạn); câu trả lời có citation không nằm trong context hoặc không ghi `[id]` trong câu trả lời thì bị chuyển thành từ chối. **Sửa một lần có log:** nếu `citations` có id nhưng câu trả lời không ghi `[id]`, hoặc (I3) query trùng query cũ, model được yêu cầu gọi lại đúng một lần. **Chọn context:** top-3 mỗi lượt, gộp theo thứ tự, bỏ trùng id; I3 dùng budget 9.600 ký tự và bỏ chunk đã thấy ở các lượt sau. **Filter:** chỉ `chapter` do câu hỏi cung cấp. **Chống rò rỉ:** agent và retriever chỉ nhận `question` và `filter`, không bao giờ nhận gold. **Lỗi:** lỗi API/DB/tool call sai định dạng được ghi `status: error` kèm thông báo, không thay bằng kết quả giả (0 lỗi ở mọi lần chạy). Nội dung tài liệu được prompt coi là dữ liệu, không phải chỉ dẫn. **Vì sao 3 lượt và top-3:** trên dev, các câu có đáp án thường xong sau 1 lượt (11/15 với I3); lượt 2-3 dùng để tìm lại với từ khác hoặc xác nhận không có bằng chứng (d16, d17 đều dùng đủ 3 lượt rồi từ chối); top-3 giữ context nhỏ (khoảng 2.000 ký tự mỗi lượt).

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| A0 / dev | 17/17 | 52 lượt gọi model; số lượt tìm: 1 lượt ×8, 3 lượt ×9 | 2/3/10 → 1,53 | 22/24 | 14/14 | 2/2 | 1/15 |
| A1 / dev | 17/17 | 49; 1×9, 2×1, 3×7 | 0/1/14 → 1,93 | 24/24 | 15/15 | 2/2 | 0/15 |
| I1 / dev | 17/17 | 50; 1×11, 2×3, 3×3 | 0/1/14 → 1,93 | 21/22 | 15/15 | 2/2 | 0/15 |
| I2 / dev | 17/17 | 51; 1×11, 2×2, 3×4 | 0/1/14 → 1,93 | 24/24 | 15/15 | 2/2 | 0/15 |
| I3 / dev | 17/17 | 50; 1×11, 2×2, 3×4 | 0/1/14 → 1,93 | 26/26 | 15/15 | 2/2 | 0/15 |
| **A0 (baseline) / test** | 7/7 | 22; 1×4, 3×3 | 0/2/3 → **1,60** | 8/8 | 5/5 | 2/2 | 0/5 |
| **I3 (đã chọn) / test** | 7/7 | 23; 1×4, 2×1, 3×2 | 0/1/4 → **1,80** | 7/7 | 5/5 | 2/2 | 0/5 |

**Chấm context cuối trên test (5 câu có đáp án, 0 = không có evidence, 1 = có nhưng thiếu, 2 = đủ evidence và nguồn):** A0: 2, 2, 2, **0** (t04), 2 → 4 câu mức 2, 1 câu mức 0. I3: 2, 2, 2, 2, 2 → 5 câu mức 2. Lý do từng câu: `results/agent-test-<config>/context_grades.json`.

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| t04 (A0) | có đáp án, trực tiếp | 3 lượt tìm (dense): "set of all possible outcomes…", "sample space set of all possible outcomes" (lặp 2 lần); context cuối không có p130:0 | "sample space" [p130:1][p131:4] | **1**: đúng nhưng hai chunk được trích không định nghĩa sample space; chunk gold p130:0 không vào context (dense hạng 4) |
| t04 (I3) | có đáp án, trực tiếp | 2 lượt (hybrid): lượt 2 "sample space definition" bỏ qua chunk đã thấy → p130:0 | "sample space" [p130:0] | **2**: trích đúng câu định nghĩa |
| t02 (cả hai) | có đáp án, có điều kiện | 1 lượt, p74:2 hạng 1 | đúng ý chính [p74:2], thêm nguyên nhân của bias không có trong p74:2 | **1** theo quy tắc chặt (khẳng định thêm không có căn cứ), giống d12 |
| t06 (cả hai) | thiếu evidence | 3 lượt (I3: 3 query khác nhau), chỉ ra chunk kỹ thuật scraping | từ chối: "không nói về tính hợp pháp, robots.txt, terms of service" | **từ chối đúng**, không thêm khẳng định |
| t07 (cả hai) | thiếu evidence | 3 lượt, ra chunk binomial/Poisson | từ chối: "không có công thức hypergeometric" | **từ chối đúng** |

- Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí: trace `results/agent-<split>-<config>/traces.json` (mỗi lượt gọi model: tool, tham số, token, chi phí, độ trễ, sửa lại; mỗi lượt tìm: query, filter, kết quả, context), nhãn `reviews.json`, chỉ số `metrics.json` (`starter/agent_metrics.py`), tóm tắt `summary.json`, so sánh `results/agent_<split>_comparison.md`. Lệnh test đã chạy (một lần mỗi cấu hình): xem `results/frozen_config.json`. Chi phí toàn bộ phần agent (5 cấu hình dev + 2 cấu hình test): khoảng $0,11 theo giá niêm yết $0,40/$1,60 mỗi 1M token (giá lấy từ trang tổng hợp bên thứ ba, cần đối chiếu với trang usage của OpenAI). Nhãn do Claude đề xuất kèm lý do, tôi kiểm tra và quyết định các trường hợp sát ranh giới (A1 d07 → 2, d12 → 1).
- Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn: trên test, I3 hơn A0 ở t04 (1 → 2) nhờ hybrid + bỏ chunk đã thấy, đúng như dự đoán từ lỗi Day 6 và từ lỗi d07 trên dev; điểm trung bình 1,60 → 1,80, Context Evidence Rate của agent 4/5 → 5/5. Cả hai đều từ chối đúng t06, t07 và không từ chối nhầm. Đánh đổi: I3 tốn hơn A0 15% ($0,00138 so với $0,00120 mỗi câu) nhưng nhanh hơn (trung vị 4,4 so với 5,3 s). **Giới hạn:** test chỉ có 7 câu (5 có đáp án), một câu thay đổi điểm trung bình 0,4, nên chênh lệch chưa có ý nghĩa thống kê; kết quả test Day 6 đã được xem trước (không dùng để chỉnh); nhãn do một người chấm, không chấm mù theo cấu hình; lỗi thêm khẳng định không có căn cứ (d12, t02) vẫn còn ở mọi cấu hình; temperature 0,01 nên chạy lại có thể khác nhẹ.

## Kết luận

- **Hybrid (dense + TF-IDF) là thay đổi có ích nhất.** Retrieval dev: Evidence Hit@3 12/15 → 13/15. Agent dev: điểm trung bình 1,53 → 1,93. Trên test, hybrid sửa được t04 ("sample space"), lỗi đã thấy từ Day 6.
- **Tìm nhiều lượt chỉ có ích khi lượt sau mang chunk mới.** Agent hay lặp query, và top-3 thường bị cùng vài chunk chiếm chỗ. Bỏ qua chunk đã thấy (I3) giúp tìm được bằng chứng còn thiếu: Context Evidence Rate của agent dev 14/15 → 15/15, test 4/5 → 5/5.
- **Từ chối đúng:** agent từ chối đúng cả 4 câu thiếu evidence (dev + test) và cấu hình chọn không từ chối nhầm câu nào.
- **Cấu hình chọn (I3) trên test:** điểm 1,80 so với baseline 1,60; chi phí khoảng $0,0014 mỗi câu.
- **Lỗi còn lại:** agent đôi khi thêm khẳng định không có trong chunk được trích (d12, t02). Đây là lỗi khi sinh câu trả lời, chưa sửa.
- **Giới hạn:** test nhỏ (5 câu có đáp án), kết quả test Day 6 đã được xem trước, chỉ một người chấm, chỉ 3 chương của một cuốn sách, giá model lấy từ trang tổng hợp bên thứ ba.
- **Nguồn:** nội dung sách từ *Principles of Data Science*, OpenStax, Rice University, CC BY-NC-SA 4.0 (Access for free at openstax.org). Khung code từ starter của khóa học (`starter/`).

## Thử thách nâng cao (nếu thực hiện)

**Không thực hiện.** Các mục dưới đây để trống.

- Tài liệu, nguồn, quyền sử dụng, số trang và phiên bản:
- Cách xử lý text, bảng, ảnh, biểu đồ; phạm vi index và phần chưa xử lý:
- Cách chia benchmark, schema evidence, model và cấu hình đã chốt trên dev:

| Nhóm test | Đạt / tổng | Tỷ lệ | Lỗi / nhận xét |
|---|---|---|---|
| Bảng | | | |
| Ảnh, sơ đồ | | | |
| Biểu đồ | | | |
| Multi-hop | | | |
| Text | | | |
| Thiếu bằng chứng | | | |
| **Toàn bộ** | | | |

- Trace, nhãn và evidence từng câu; thời gian, chi phí, lỗi hệ thống:
- Giới hạn, cách tái lập và đường dẫn benchmark:
