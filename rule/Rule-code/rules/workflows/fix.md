# WORKFLOW — FIX (sửa bug / lỗi)

Áp dụng thêm `01_core.md`. Nguyên tắc: root cause trước, sửa tối thiểu, không vá triệu chứng.

## Các bước

**B1 — Thu thập bằng chứng**
Lấy thông báo lỗi, stack trace, log nguyên văn (user dán hoặc Read file log trong dự án). User chỉ mô tả mơ hồ thì 1 Question xin lỗi gốc hoặc các bước tái hiện.

**B2 — Định vị**
Theo symbol/dòng trong stack: Grep → Read đúng vùng. Có Map thì dùng để định vị (Map chỉ là gợi ý, `01_core.md` §18). Codebase lớn: Task explore.

**B3 — Reproduce**
Cần chạy lệnh thì qua L3. Không được phép/không chạy được: dựa vào bằng chứng user cung cấp và ghi rõ root cause là `[ASSUMED]`.

**B4 — Root cause**
Một giả thuyết mỗi lần; chứng minh bằng Read/Grep/output. Ghi: `Root cause: <file:line> vì <bằng chứng>`. Không đoán mò.

**B5 — Fix tối thiểu**
Edit đúng chỗ gây lỗi. Không đổi kiến trúc, không thêm tính năng, không refactor, không sửa bug khác. Hai fix liên tiếp thất bại: dừng, báo user, xem lại giả định (`01_core.md` §15).

**B6 — Verify**
Chạy lại kịch bản lỗi (nếu được phép) + chức năng liên quan. Dự án có test thì thêm ca tái hiện bằng Edit vào file test có sẵn (`01_core.md` §14). Không chạy được: `NOT RUN` + lệnh.

**B7 — Sync + dọn**
Thường N/A; nếu file/dependency đổi thì theo §18. Dọn theo §6. Bug tương tự ở nơi khác: chỉ báo, không sửa. Flow có dùng TodoWrite thì append 1 entry `PROGRESS.md` (§21) khi xong.

## Checklist
- [ ] Root cause có bằng chứng `file:line` (hoặc ghi `[ASSUMED]`)
- [ ] Diff nhỏ nhất; không chạm code không liên quan
- [ ] Đã verify lại lỗi cũ + tính năng liên quan, hoặc `NOT RUN` + lệnh
- [ ] Không còn code debug / file repro tạm

## Report mẫu
```text
Bug: <mô tả ngắn>
Root cause: <file:line — vì sao> [VERIFIED|ASSUMED]
Changed: <file:range>
Verified: <repro trước/sau + kết quả thật>   NOT RUN: <lệnh cho user>
Similar issues (không sửa): <vị trí|none>
Risks: ...   Cleanup: none | LEFTOVER: ...
```
