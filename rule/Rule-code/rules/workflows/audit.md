# WORKFLOW — AUDIT (đọc toàn bộ source → `ARCHITECTURE.md` + `PROJECT_MAP.json`)

Áp dụng thêm `01_core.md`. Chỉ đọc source; chỉ GHI đúng 2 file `ARCHITECTURE.md` và `PROJECT_MAP.json` ở root dự án. `PROJECT_BLUEPRINT.mmd` chỉ khi user yêu cầu. Không tạo `UI_SPEC.json`/`UI_PREVIEW.html`. Không sửa code, không đề xuất kiến trúc mới như thể là hiện trạng.

## Các bước
**B1 — Đọc toàn bộ source**
1. Glob liệt kê file; Read manifest và config trước (package/build file, entry point).
2. TodoWrite: mỗi thư mục nguồn một mục để theo dõi độ phủ. Dự án lớn: dùng Task explore theo từng thư mục (prompt theo `01_core.md` §2).
3. Chỉ bỏ qua file sinh tự động, vendored, binary, lock file — và **liệt kê những gì đã bỏ qua**.

**B2 — Phân tích kiến trúc hiện có:** cấu trúc, luồng chạy, module/component, quan hệ, dependency, data flow, entry point, DB/API, pattern nhận ra được. Mô tả hiện trạng, không thiết kế lại.

**B3 — Write `PROJECT_MAP.json`** (`map_type:"actual"`):
`schema_version:"1.0"`, `map_type`, `generated_at`, `git_commit?` (`01_core.md` §18), `scale?`, `entry_points[]`, `modules[{path,type,module?,responsibility,feature[],dependencies[],symbols[],status:"exists"}]` (`symbols` bắt buộc cho file source), `external_dependencies[{name,version?,reason}]`, `skipped[]`. Không xác định được feature thì ghi `"feature": []`, không đoán. Không bịa thông tin không có trong source.

**B4 — Write `ARCHITECTURE.md`:** cấu trúc dự án, workflow, data flow, module/file, dependency, entry point, DB/API/tích hợp, thành phần quan trọng và quan hệ. Vấn đề quan sát được ghi riêng ở mục "Observations".
File đã tồn tại thì Read trước rồi cập nhật/ghi lại đúng đường dẫn đó; không để bản `.old`/`.bak`.

**B5 — Validate:** đối chiếu Map ↔ ARCHITECTURE ↔ source: Grep kiểm mẫu các `symbols` và `path` trong Map có thật. Lệch thì đọc lại source và sửa.

## Checklist
- [ ] Đã phủ toàn bộ source (trừ phần bỏ qua có liệt kê trong `skipped`)
- [ ] Map và ARCHITECTURE khớp source, không mâu thuẫn nhau
- [ ] Chỉ tạo/sửa đúng 2 file; không sửa source
- [ ] Không bịa symbol/feature/dependency

## Report mẫu
```text
Audit: <n> file đọc / <m> bỏ qua (skipped: <loại>)
Output: ARCHITECTURE.md, PROJECT_MAP.json (map_type actual, git_commit <hash|bỏ>)
Observations (không sửa): <vài dòng>
Verified: Grep kiểm mẫu <k> symbol/path — khớp.   NOT RUN: n/a
Cleanup: none
```
