# WORKFLOW — REVIEW (chỉ đọc, KHÔNG sửa)

Áp dụng thêm `01_core.md`. Nên ở Plan mode. Tuyệt đối không Edit/Write file nào; không tạo file báo cáo trừ khi user yêu cầu.

## Các bước

**B1 — Xác định phạm vi** user yêu cầu (file/module/PR diff đã có trong dự án). Có `PROJECT_MAP.json` thì Read Map + `ARCHITECTURE.md` để định vị; codebase lớn thì Task explore. Không đọc ngoài phạm vi.

**B2 — Đọc source thật** của phạm vi (Map chỉ để định vị).

**B3 — Kiểm tra:** đúng đắn; bảo mật (`01_core.md` §13); xử lý lỗi; edge case; lãng phí hiệu năng; cấu trúc so với `ARCHITECTURE.md`; maintainability; test; dependency. Muốn chạy test để kiểm chứng thì hỏi qua L3.

**B4 — Báo cáo theo mức độ**
- **Critical** — lỗ hổng bảo mật, mất dữ liệu, crash luồng chính.
- **Major** — bug chức năng, khả năng regression, vỡ contract.
- **Minor** — maintainability, đặt tên, kém hiệu quả nhỏ.
- **Info** — quan sát, gợi ý.

Mỗi finding: vị trí (`file:line`), vấn đề, vì sao quan trọng, gợi ý sửa, nhãn `[VERIFIED]`/`[ASSUMED]`.

**B5 — Kết thúc bằng Question:** muốn sửa finding nào. Sửa chỉ khi user chọn, và chuyển sang `fix.md`/`refactor.md` tương ứng.

## Checklist
- [ ] Không file nào bị sửa/tạo
- [ ] Mỗi finding có `file:line` + bằng chứng
- [ ] Đã sắp theo severity; đã hỏi user muốn sửa gì

## Report mẫu
```text
Scope: <đã đọc gì> (không đọc: <...>)
Critical: <n> | Major: <n> | Minor: <n> | Info: <n>
1. [Major] src/x.js:42 — <vấn đề>. Vì sao: <...>. Gợi ý: <...>. [VERIFIED]
...
Changed: không sửa file.   Hỏi: sửa mục nào?
```
