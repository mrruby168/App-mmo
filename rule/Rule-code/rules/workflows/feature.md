# WORKFLOW — FEATURE (thêm/đổi hành vi trong dự án có sẵn)

Áp dụng thêm `01_core.md`. Mục tiêu: thêm đúng tính năng, sửa ít nhất, không phá cái đang chạy.

## Các bước

**B1 — Định vị**
- Case 1 (có `PROJECT_MAP.json`): Read Map → `ARCHITECTURE.md` → (`REQUIREMENTS.json`, `UI_SPEC.json` chỉ khi cần). Freshness check: so `git_commit` của Map với hash đọc từ `.git\HEAD` (`01_core.md` §18), hoặc spot-check 2–3 symbol bằng Grep. Có vẻ cũ thì coi Map chỉ là gợi ý và ghi "Map stale".
- Case 2 (không có Map): đọc đủ source cần để hiểu cấu trúc và logic (Task explore nếu codebase lớn). Xong việc, đề nghị chạy `workflows/audit.md`.
- Dùng Grep/Glob thu hẹp. Không đọc toàn bộ source khi scope đã rõ.

**B2 — Chốt scope + acceptance criteria**
Viết 2–5 gạch đầu dòng tiêu chí chấp nhận. Chưa rõ thì 1 Question; đã rõ thì bỏ qua.

**B3 — Impact**
Đánh giá module, data, UI, dependency bị ảnh hưởng. Trải nhiều module hoặc thêm subsystem mới thì khuyên làm Phase 1 DESIGN của `workflows/new_app.md` cho phần thay đổi và hỏi user.

**B4 — Plan**
Từ 3 bước trở lên: TodoWrite (mục tiêu, file, test). Luôn thêm `VERIFY` và `CLEANUP + REPORT`.

**B5 — Implement**
Grep tái dùng hàm/class/style có sẵn. Sửa bằng Edit (`01_core.md` §4); theo kiến trúc và style hiện có. Mỗi lượt một thay đổi logic.

**B6 — Verify + validate**
Theo `01_core.md` §5: Read-back, Grep chéo, T1/T2 (+T3 nếu dự án có test). Đối chiếu từng tiêu chí chấp nhận. Grep nơi gọi của chỗ đã sửa để kiểm tra không phá tính năng liên quan.

**B7 — Sync + dọn**
Theo `01_core.md` §18 (Map, `ARCHITECTURE.md`, `REQUIREMENTS.json` nếu có thêm feature, `UI_SPEC.json` nếu UI đổi). Dọn theo §6. Flow có dùng TodoWrite thì append 1 entry `PROGRESS.md` (§21) khi xong.

## Checklist
- [ ] Mỗi tiêu chí chấp nhận đã verify hoặc ghi `NOT RUN`
- [ ] Không tạo file mới không cần thiết; không sửa lan
- [ ] Tái dùng code có sẵn thay vì viết trùng
- [ ] Artefact đã sync hoặc đánh dấu stale
- [ ] Không còn file tạm / code debug

## Report mẫu
```text
Feature: <tên> — acceptance: <tiêu chí 1..n: đạt / NOT RUN>
Changed: <file:range ...>
Verified: <T1/T2/T3 + kết quả>   NOT RUN: <lệnh/bước cho user>
Assumptions / Risks: ...
Sync: PROJECT_MAP.json <updated|N/A|stale>; ARCHITECTURE.md <updated|N/A>
Cleanup: none | LEFTOVER: ...
Tip: nhiều file đã đổi — dùng /undo nếu muốn hoàn tác lượt này.
```
