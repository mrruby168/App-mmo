# WORKFLOW — NEW APP (Phase 1 DESIGN → duyệt → Phase 2 BUILD)

Áp dụng thêm `01_core.md`. Thư mục dự án phải nằm trong `D:\AI-AGENT\` (L1); chưa rõ thì hỏi bằng Question. Artefact đặt ở root dự án.

# PHASE 1 — DESIGN

### B1 — Scale + có UI không
Đề xuất Small/Medium/Large và `has_ui` từ những gì user đã nói (Question để user xác nhận).

### B2 — Form (Question, từng câu)
Hỏi theo scale; mỗi mức gồm cả mức trước. Giá trị bạn tự đề xuất ghi `status: "proposed"` cho đến khi user chấp nhận. **Không** chốt thay user bất cứ thứ gì ảnh hưởng mục tiêu/chức năng.
- **Small:** mục tiêu; người dùng; chức năng chính; workflow chính; loại giao diện (GUI/Web/Mobile hoặc None); nền tảng; lưu trữ dữ liệu (không/file/DB); công nghệ-ràng buộc *(tùy chọn)*; ngôn ngữ tài liệu *(tùy chọn)*.
- **Medium +:** tính năng chi tiết (mô tả + ưu tiên); vai trò; workflow chi tiết; entity dữ liệu; database; API/tích hợp; authentication; deployment; ràng buộc.
- **Large +:** business logic; system workflow; data flow; permission; security; performance/scalability; external services; infrastructure; backup/recovery; monitoring/logging; mở rộng tương lai; ràng buộc kỹ thuật.
- **Có UI:** hỏi thêm cách thiết kế UI/UX: `RULE_DEFAULT` / `AI_DESIGN` / `EXTERNAL_REFERENCE`. Không UI: mô tả giao diện (lệnh CLI, endpoint API, hàm public).

Thiếu trường bắt buộc thì hỏi tiếp. Tóm tắt lại, user xác nhận, rồi Write `REQUIREMENTS.json`:
`schema_version:"1.0"`, `scale`, `has_ui`, `ui_requirement_mode`, `external_reference?`, `document_language`, `objective`, `users[]`, `features[{id:"F-01", name, description, priority:must|should|could, status:confirmed|proposed}]`, `workflow`, `platform`, `data_storage`, `technology?`, `constraints[]`, `medium{roles,data_entities,database,api_integration,authentication,deployment}?`, `large{business_logic,system_workflow,data_flow,permissions,security,performance_scalability,external_services,infrastructure,backup_recovery,monitoring_logging,future_expansion,technical_constraints}?`, `confirmed_by_user:true`.

### B3 — UI/UX (bỏ qua nếu `has_ui=false`)
- `RULE_DEFAULT`: lưới 4px; spacing `4/8/12/16/24/32/40/48/64`; container max 1200, padding 24; button cao 40 (nhỏ 32, lớn 48), radius 8; input cao 40, radius 8; card radius 12; modal radius 12, rộng 480–640; tối đa 2 font family; cỡ chữ H1 32 / H2 24 / H3 20 / body 16 / small 14 / caption 12, line-height body 1.5; một bộ icon; vai trò màu primary, secondary, background, surface, text, muted_text, border, success, warning, error, info; breakpoint mobile <640, tablet 640–1023, desktop ≥1024; state `default/hover/active/focus/disabled` và `loading/success/error/empty`; contrast WCAG AA (4.5:1 chữ thường, 3:1 chữ lớn/UI), touch target ≥44×44, không chỉ dùng màu để báo trạng thái.
- `AI_DESIGN`: tự thiết kế từ Form; không đổi chức năng đã chốt.
- `EXTERNAL_REFERENCE`: xin nguồn từ user (URL → WebFetch, file → Read trong `D:\AI-AGENT`); phân tích style/layout/component; so với Form (giữ/đổi/thêm); thảo luận điểm xung đột; chờ user chốt rồi mới thiết kế. Không chép nội dung/asset không được phép dùng.
- Output đúng 2 file: `UI_SPEC.json` (bản chuẩn) gồm `schema_version`, `design_mode`, `spacing_scale_px`, `layout{screens[{id,name,regions,features}],container_max_width_px,screen_padding_px}`, `typography`, `colors{light,dark?}`, `components[{name,dimensions,spacing,states,interaction}]`, `responsive`, `accessibility`; và `UI_PREVIEW.html` (wireframe, không PNG — `01_core.md` §19).

### B4 — Kiến trúc
Đọc `REQUIREMENTS.json` (+ `UI_SPEC.json`). Chuỗi: REQUIREMENT → UI/UX → WORKFLOW → ARCHITECTURE → CODE STRUCTURE. Kiến trúc vừa với scale (Small = ít module, cấu trúc phẳng; không over-engineer).
- `ARCHITECTURE.md`: tổng quan, workflow, data flow, layer/module + trách nhiệm, dependency (kèm lý do), cấu trúc thư mục/file, entry point, quyết định kỹ thuật, quy tắc tổ chức code. Large thêm rủi ro và lý do quyết định lớn.
- `PROJECT_MAP.json` (`map_type:"planned"`): `schema_version:"1.0"`, `generated_at`, `scale`, `entry_points[]`, `modules[{path,type,responsibility,feature[F-xx],dependencies[],status:"planned"}]`, `external_dependencies[{name,version?,reason}]`.
- `PROJECT_BLUEPRINT.mmd` (Mermaid): bắt buộc Medium/Large, tùy chọn Small.
- Kiểm nhất quán: REQUIREMENTS ↔ UI_SPEC ↔ ARCHITECTURE ↔ PROJECT_MAP ↔ BLUEPRINT. Còn mâu thuẫn thì chưa giao.

### B5 — Bàn giao
Question: "Duyệt Design Pack" / "Cần chỉnh". Chỉ sang Phase 2 sau khi user duyệt (hoặc user đã nói rõ cứ tiếp tục không dừng).

# PHASE 2 — BUILD

### B1 — Đọc Design Pack (theo thứ tự)
`REQUIREMENTS.json` → `UI_SPEC.json` (nếu có UI) → `ARCHITECTURE.md` → `PROJECT_MAP.json` → `PROJECT_BLUEPRINT.mmd` (nếu có). Đọc hết rồi mới lập kế hoạch. Không thêm tính năng ngoài Design Pack.

### B2 — Kế hoạch WI (TodoWrite)
Chia WI theo thứ tự Core → Feature → Integration → Testing, WI đủ nhỏ để Code → Test → Done độc lập. Mỗi WI ghi: ID + tên, mục tiêu, file/module, phụ thuộc WI khác, điều kiện xong, test (mức T1/T2/T3). Small: danh sách ngắn (mục tiêu, file, test). Đối chiếu kế hoạch với `ARCHITECTURE.md`, `PROJECT_MAP.json`, `UI_SPEC.json` trước khi code; lệch thì sửa kế hoạch trước.

### B3 — Code từng WI
`Analyze → Code → Test → Validate → Done`. Trạng thái bằng prefix trong TodoWrite: `[CODING]`, `[TESTING]`, `[BLOCKED]`. Báo tiến độ sau mỗi WI, append `PROGRESS.md` (§21) ngay sau báo cáo chat, và liệt kê `STUB(<wi-id>)` đang còn (`01_core.md` §8).
- Vẫn Glob trước khi Write (thư mục/file có thể đã tồn tại); file theo Map planned thì tạo ngay (Blueprint exception).
- Không có Bash: chỉ Write file; lệnh `npm init`/cài gói/build đều là `NOT RUN` + lệnh cho user. Nếu dùng Bash: qua L3, không chạy server/watch nền — cần user cho phép trước.
- Test: Happy Path, Edge Case, Error Case.

### B4 — WI = DONE khi
Code đầy đủ; chức năng chính đã verify (`01_core.md` §5); không còn lỗi nghiêm trọng của WI; file/module liên quan đã cập nhật; không phá WI trước; không còn `STUB` của WI.
User từ chối cho chạy lệnh: WI chỉ được ghi `DONE-UNVERIFIED` (kèm lệnh cho user); dự án chỉ được gọi `CODE-COMPLETE, UNVERIFIED`, không gọi `COMPLETED`. Mọi WI DONE (kể cả `DONE-UNVERIFIED`) phải có entry `PROGRESS.md` mới được tính xong.

### B5 — Change control trong lúc code
| Loại | Ví dụ | Hành động |
|---|---|---|
| Minor | Thêm helper nội bộ, đổi tên file; trách nhiệm/dependency không đổi | Làm tiếp, cập nhật Map |
| Design change | Đổi trách nhiệm module, dependency, data flow, công nghệ | Dừng WI, báo user kèm đề xuất; sau duyệt cập nhật `ARCHITECTURE.md`, Map, Blueprint |
| Requirement/UI change | Thêm/bỏ/đổi tính năng; UI khác thiết kế | Hỏi user; sau xác nhận cập nhật `REQUIREMENTS.json`/`UI_SPEC.json` và hạ nguồn |
WI bị chặn: ghi `[BLOCKED]`, làm tiếp WI độc lập.

### B6 — Validate toàn dự án
Đối chiếu chức năng, UI/UX, workflow, kiến trúc, DB/API, xử lý lỗi, dependency, cấu trúc code với Requirement. Sửa lỗi trước khi xác nhận hoàn tất.

### B7 — Kết thúc
Đặt `PROJECT_MAP.json` thành `map_type:"actual"` (thêm `symbols`, `git_commit` nếu đọc được, `generated_at`); cập nhật `ARCHITECTURE.md`/Blueprint nếu thiết kế đổi. Dọn rác (`01_core.md` §6). Append mục `COMPLETED` chốt vào `PROGRESS.md`.

## Checklist
- [ ] Phase 1: Form đã được user xác nhận; Design Pack nhất quán; user đã duyệt trước khi code
- [ ] Mọi tính năng trong `REQUIREMENTS.json` đã có code; không có tính năng ngoài Design Pack
- [ ] Không còn `STUB`; Map `actual` khớp code; cấu trúc khớp `ARCHITECTURE.md`
- [ ] Mọi lệnh đã chạy đều có permission; phần chưa chạy ghi `NOT RUN`

## Report mẫu
```text
Design: scale <S/M/L>, UI <có/không>, Design Pack: <danh sách file> — user approved: <có/không>
WI: WI-1 DONE | WI-2 DONE | WI-3 DONE-UNVERIFIED (lý do)
Changed: <file mới/sửa chính>
Verified: <T1/T2/T3 + kết quả thật>   NOT RUN: <lệnh cho user>
Assumptions / Risks: ...
Map: PROJECT_MAP.json actual (git_commit <hash|bỏ>)
Cleanup: none | LEFTOVER: ...
```
