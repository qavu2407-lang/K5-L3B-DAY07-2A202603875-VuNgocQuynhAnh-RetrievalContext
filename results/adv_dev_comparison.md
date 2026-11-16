# So sánh các cấu hình trên dev — thử thách nâng cao

Tài liệu: *Principles of Data Science* (OpenStax), chương 5, 6, 9. Bộ dev: 18 câu (15 có đáp án + 3 thiếu bằng chứng), `data/advanced/benchmark.json`. Mỗi câu chấm **đạt / không đạt** bằng cách đối chiếu với PDF gốc; nhãn và lý do từng câu nằm trong `labels.json` của từng thư mục kết quả.

## Thiết lập chung

- Agent: OpenAI `gpt-4.1-mini`, temperature 0,01, tìm kiếm hybrid (dense + TF-IDF, RRF), tối đa 3 lượt tìm, top-3 mỗi lượt, context 9.600 ký tự, không cho lặp query, lượt tìm sau bỏ qua chunk đã thấy (giống cấu hình I3 của phần cơ bản).
- Mỗi dòng trong bảng **thêm một thay đổi** so với dòng trước (trừ O1 và các lần chạy lặp "b").
- Tên I3–I8 ở đây là cấu hình của phần nâng cao, **không phải** I1–I3 của phần cơ bản; I3 nâng cao bắt đầu từ đúng thiết lập của I3 cơ bản.

## Phiên bản index

Index thay đổi trong quá trình thử, nên kết quả chỉ so sánh trực tiếp được giữa các lần chạy cùng phiên bản.

| Phiên bản | Thay đổi | Dùng cho |
|---|---|---|
| v0 | Text, bảng (PyMuPDF), mô tả hình bằng `gpt-4.1-mini` vision | I3–I5 |
| v1 | + 5 bảng mất ô công thức được chép lại từ ảnh; mô tả biểu đồ cột/histogram viết lại (liệt kê từng cột) | I6–I8, F1 |
| v1-OCR | Như v1 nhưng hình đọc bằng Tesseract 5.5.2; chỉ dùng mô tả vision khi OCR thất bại (57/86 hình dùng OCR) | O1 |
| v2 | v1 + chú thích thay thế cho 35 hình không có caption (đoạn văn ngay trước và sau hình) | F2, F2b, F3, F3b |
| v3 | v2 + 254 đoạn văn có công thức (vẽ bằng vector, mất ký hiệu trong lớp text) được chép lại từ ảnh; 9 bản chép bị loại vì thêm nội dung không có trong sách | F4, F4b (index hiện tại) |

Chỉ F4/F4b chạy lại được trên index hiện tại; các lần chạy trước vẫn giữ nguyên trace làm bằng chứng.

## Kết quả

| Cấu hình | Thay đổi so với dòng trước | Index | Đạt / 18 | Câu không đạt | Chi phí ($) | Thời gian trung vị (s/câu) |
|---|---|---|---|---|---|---|
| I3 | Thiết lập I3 của phần cơ bản, prompt v2 | v0 | 12 | AD06, AD08, AD09, AD11, AD14, AD17 | 0,027 | 3,9 |
| I4 | Prompt v3: chỉ trả lời điều được hỏi, kiểm tra đúng ví dụ | v0 | 10 | AD06, AD08, AD09, AD10, AD11, AD12, AD13, AD14 | 0,033 | 3,9 |
| I5 | Tìm kiếm có thể giới hạn bảng / hình / text | v0 | 13 | AD06, AD08, AD10, AD11, AD17 | 0,039 | 4,2 |
| I6 | Prompt v4 + công cụ tính toán | v1 | 13 | AD06, AD10, AD11, AD14, AD17 | 0,041 | 3,8 |
| I7 | Sửa định dạng citation `[a, b]` → `[a][b]` | v1 | 13 | AD04, AD06, AD11, AD14, AD17 | 0,041 | 4,0 |
| I8 | Tự thêm `[id]` còn thiếu sau một lần sửa thất bại | v1 | 13 | AD06, AD10, AD11, AD14, AD17 | 0,039 | 3,6 |
| O1 | I8 trên index OCR (thử nghiệm thay thế, không cải thiện) | v1-OCR | 10 | AD04, AD05, AD06, AD07, AD09, AD11, AD14, AD17 | 0,036 + 0,002 embedding | 5,8 |
| F1 | I8 + công cụ `read_figure`: gửi ảnh crop + câu hỏi cụ thể cho `gpt-6.1-terra`; prompt v5 | v1 | 15 | AD11, AD14, AD17 | 0,058 | 7,3 |
| F2 | + chú thích thay thế cho hình; prompt v6 (tìm cả bảng và hình, số phải đúng ví dụ, không tự điền ký hiệu bị mất) | v2 | 15 | AD10, AD11, AD17 | 0,058 | 5,6 |
| F2b | Chạy lại F2, cùng thiết lập | v2 | 15 | AD11, AD14, AD17 | 0,054 | 5,4 |
| F3 | + nhắc tìm hình khi câu hỏi nói đến biểu đồ/hình; + bước kiểm tra (verify) câu trả lời với chunk được trích | v2 | 16 | AD14, AD17 | 0,088 | 7,5 |
| F3b | Chạy lại F3 | v2 | 16 | AD14, AD17 | 0,084 | 7,9 |
| F4 | Cấu hình F3 trên index v3 (công thức được chép lại) | v3 | 16 | AD11, AD17 | 0,083 | 8,2 |
| F4b | Chạy lại F4 | v3 | 17 | AD17 | 0,084 | 8,4 |

Không có lỗi hệ thống ở các lần chạy trên. Chi phí gồm model agent, verify và vision của `read_figure`; giá `gpt-4.1-mini` $0,40 / $1,60 và `gpt-6.1-terra` $1 / $5 mỗi 1M token input / output. Chi phí xây index: vision $0,166 (91 mô tả hình/bảng + 263 đoạn công thức), embedding dưới $0,01.

## Nhận xét

- **Đọc hình theo câu hỏi là thay đổi có ích nhất.** Nhóm câu hình (AD04–AD09): I8 đạt 5/6 (AD06 sai do mô tả hình ghi nhầm Mỹ ≈ 50.000 ca; kiểm tra màu điểm ảnh cho thấy Mỹ ở dải 1.000–5.000), từ F1 trở đi đạt 6/6 ở mọi lần chạy.
- **OCR không thay được vision (O1).** Tesseract đọc đúng chữ in nhưng mất thông tin đồ họa (cột cao nhất, hình dạng đường, nhánh cây quyết định); độ tin cậy OCR cao ngay cả khi kết quả vô dụng. Nhóm câu hình giảm còn 1/6.
- **Lỗi do ký hiệu toán bị mất (AD14)** chỉ hết khi sửa ở index (v3); các quy tắc trong prompt không đủ.
- **Biến động giữa các lần chạy:** cùng thiết lập, kết quả lệch khoảng 1 câu (F2/F2b, F4/F4b).
- **Lỗi còn lại:** AD17 (câu bẫy: điểm silhouette 0,77 thuộc lần chạy Python trên 115 điểm, không phải ví dụ 19 điểm) sai ở mọi cấu hình.
- **Nhãn sát ranh giới:** AD11 ở F3, F3b, F4b được chấm đạt — đúng ba nhóm lỗi và tỷ lệ khoảng 76% (đúng: 76,3%), nhưng dựa vào giá trị đọc gần đúng từ biểu đồ hoặc cách diễn đạt "khoảng 75%" của sách thay vì phép tính từ bảng.

Trace từng câu: `results/adv-agent-dev-<cấu hình>/traces.json` (O1: `results/adv-ocr-agent-dev-O1/`). Cấu hình được chọn và tiêu chí chọn sẽ ghi riêng trước khi chạy test.
