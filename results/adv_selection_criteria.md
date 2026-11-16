# Tiêu chí chọn cấu hình — thử thách nâng cao

Viết ngày 2026-11-16, **sau** các lần chạy dev I3–F4b và **trước** khi chạy test. Chưa có câu test nào được chạy hay xem kết quả. Bảng dev đầy đủ: `results/adv_dev_comparison.md`.

## Ứng viên

Mọi cấu hình đã chạy trên 18 câu dev: I3–I8, O1, F1, F2/F2b, F3/F3b, F4/F4b, F5/F5b, F6/F6b (F5–F6b thêm sau, xem phụ lục).

## 1. Điều kiện bắt buộc

Cấu hình không đủ điều kiện nếu vi phạm một trong các điều sau:

- Có lỗi hệ thống (model, vector store, timeout) ở bất kỳ lần chạy dev nào.
- Không đạt cả 3 câu thiếu bằng chứng (AD16–AD18) ở mọi lần chạy.
- Đạt dưới **16/18** ở bất kỳ lần chạy dev nào. Ngưỡng 90% của test tương đương 16,2/18; vì kết quả lệch khoảng 1 câu giữa các lần chạy, chỉ giữ cấu hình đạt ít nhất 16/18 **ở cả hai** lần chạy cùng thiết lập.
- Chi phí trên **$0,10** cho 18 câu.
- Không chạy lại được trên index hiện tại (`data/advanced/chunks.json`), vì test phải dùng đúng pipeline đã chốt.

## 2. Chỉ số chính

Số câu đạt trung bình trên các lần chạy cùng thiết lập (nhãn đạt / không đạt theo `ADVANCED.md`, đối chiếu PDF gốc).

## 3. Phân định khi bằng nhau

1. Ít câu không đạt xuất hiện ở mọi lần chạy (lỗi ổn định) hơn.
2. Chi phí mỗi câu thấp hơn.
3. Thời gian trung vị mỗi câu thấp hơn.

## Áp dụng

| Cấu hình | Lần chạy | Đạt | Điều kiện 1 |
|---|---|---|---|
| I3–I8, O1, F1, F2/F2b | 1 hoặc 2 | 10–15 | loại: dưới 16/18 |
| F3 / F3b | 2 | 16, 16 | loại: chạy trên index v2, không còn tái lập được |
| **F4 / F4b** | 2 | 16, 17 (trung bình 16,5) | **đủ điều kiện**: không lỗi, 3/3 câu thiếu bằng chứng, $0,083–0,084, index hiện tại |

| F5 / F5b | 2 | 17, 17 (trung bình 17) | không lỗi; chi phí $0,094 và $0,103 — vượt $0,10 ở F5b |
| F6 / F6b | 2 | 18, 17 (trung bình 17,5) | không lỗi; chi phí $0,110 và $0,112 — **vượt $0,10 ở cả hai lần** |

(Bảng ban đầu chỉ có I3–F4b và chọn F4. F5–F6b được thêm sau, vẫn trước khi chạy test; xem phụ lục.)

## Phụ lục — đổi lựa chọn sang F6 (2026-11-16, trước khi chạy test)

Sau khi viết tiêu chí trên, đã thử thêm trên dev: F5/F5b (đoạn văn sau bảng/hình, prompt v7, prompt đọc hình v2, verify không dùng mô tả lưu sẵn của hình đã đọc) và F6/F6b (F5 + verify bằng `gpt-6.1-terra`). Bảng dev: `results/adv_dev_comparison.md`.

**Chọn: F6** (trung bình 17,5/18, cao nhất; là cấu hình duy nhất có lần chạy bắt được câu bẫy AD17).

**Sai lệch so với tiêu chí viết trước:** F6 **không** đạt điều kiện chi phí ($0,10 cho 18 câu): $0,110 và $0,112. Theo đúng tiêu chí ban đầu, F4 vẫn là cấu hình đủ điều kiện duy nhất. F6 được chọn sau khi đã xem kết quả dev của F5/F6 (không phải kết quả test — test chưa chạy). Sai lệch này được báo trong báo cáo.

Lưu ý nhãn: các nhãn F5–F6b có một số câu sát ranh giới (AD06, AD09, AD11, AD16 — ghi "BORDERLINE" trong `labels.json`). Nếu các nhãn này bị chấm không đạt, F6 vẫn ≥ 16/18 ở cả hai lần chạy.

## Quy trình test

Chốt cấu hình trong `results/adv_frozen_config.json`, chạy F6 trên toàn bộ 30 câu test **một lần** với `--confirm-frozen`, chấm từng câu đạt / không đạt kèm lý do và đối chiếu bản gốc. Không sửa pipeline, prompt hay index sau khi xem kết quả test. Lỗi hệ thống, timeout hoặc không có kết quả tính là không đạt và báo riêng.
