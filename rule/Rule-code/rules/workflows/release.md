# WORKFLOW — RELEASE / MANAGE (git, version, dependency, build, test, release, deploy, backup, rollback, status, sync, audit quản lý)

Áp dụng thêm `01_core.md`. Mọi lệnh theo L3, mọi thao tác git ghi theo L4, mọi path ngoài `D:\AI-AGENT` theo L1. Không chạy server/watch nền — cần user cho phép trước.

## Các bước
**B1 — Nhận dự án:** xác nhận thư mục dự án. Read cấu trúc, config, manifest, `.git\HEAD`, file version.
**B2 — Chọn đúng 1 mode** bằng Question. Không làm việc ngoài mode.
**B3 — Phân tích:** phạm vi, file liên quan, rủi ro, điều kiện hoàn tất. Phải có lệnh thì lập danh sách lệnh cho L3.
**B4 — Thực thi:** `Analyze → Plan → Execute → Test → Validate → Report`. Việc thuộc High-Risk (`01_core.md` §17): báo và xin xác nhận TRƯỚC.
**B5 — Validate:** dự án chạy bình thường, không mất dữ liệu, git không hỏng, version đúng, build/deploy hiện tại không vỡ, Map/tài liệu đã sync.

## Các mode
| Mode | Làm gì | Ràng buộc |
|---|---|---|
| STATUS | Báo nhánh/commit hiện tại (Read `.git\HEAD` + ref), version, dependency, trạng thái build/test. Trạng thái làm việc/uncommitted cần `git status` → L3, không cho chạy thì `NOT RUN`. | Không thay đổi dự án. |
| GIT | Xem branch/commit/diff (qua L3). | Commit/branch/push/PR chỉ khi user yêu cầu đích danh (L4). Không `reset --hard`, `clean`, `push --force`, `branch -D` khi chưa xác nhận (§17). |
| VERSION | Kiểm version hiện tại, thống nhất mọi nơi ghi version, ghi lịch sử version. | Chỉ tăng version khi user yêu cầu hoặc quy trình release quy định. |
| DEPENDENCY | Read manifest/lock; kiểm phiên bản, tương thích, rủi ro, xung đột. Lệnh kiểm tra (vd `npm outdated`) dùng mạng → nói rõ trong Question. | Không nâng cấp hàng loạt; test lại dependency quan trọng sau khi đổi. |
| BUILD | Kiểm build config, môi trường, chạy build, kiểm artifact. | Không đổi build config nếu không cần. |
| TEST | Chạy test phù hợp (T1/T2/T3). | Không bao giờ báo PASS nếu chưa chạy thật. |
| RELEASE | Trước release kiểm: version, git status, test, build, dependency, config, changelog. Xác định rõ version và source chính xác. | Tạo tag/commit chỉ khi user yêu cầu (L4); không thì đưa lệnh cho user. |
| DEPLOY | Xác định môi trường, đích, version, artifact, config, cách deploy. Thứ tự Development → Staging → Production. | Đích ngoài `D:\AI-AGENT` → L1. Production: chỉ khi user nêu rõ môi trường và xác nhận (High-Risk). Sau deploy kiểm hệ thống thật. |
| BACKUP | Đích backup do user chọn (trong `D:\AI-AGENT`, không phải `OPENCODE`). Copy source/config/data cần thiết; Glob đích để xác nhận tồn tại. | Chưa xác nhận tồn tại thì không coi là đã có backup. |
| ROLLBACK | Chỉ khi user yêu cầu. Xác định version/commit/backup đích; backup trạng thái hiện tại trước; validate sau. | Lệnh git ghi theo L4. |
| SYNC | Đồng bộ source ↔ git ↔ version ↔ Map ↔ tài liệu (`01_core.md` §18). Map nghi cũ: hỏi user rồi chạy `workflows/audit.md`. | — |
| AUDIT (quản lý) | Kiểm tổng thể git, version, dependency, cấu trúc cấp cao, config, build, test, bảo mật, deploy, tài liệu; đề xuất cách xử lý. | Không sửa code. Yêu cầu đọc toàn bộ source hoặc tạo Map thì dùng `audit.md`. |
| FULL | Chuỗi STATUS → GIT → VERSION → DEPENDENCY → BUILD → TEST → RELEASE → DEPLOY → SYNC. | Chốt phạm vi trước; không phải bước nào cũng cần. |

## Quy tắc chung
- Secret: bảo vệ theo `01_core.md` §13; không đưa vào log, output, commit. Thấy secret lộ thì cảnh báo user ngay.
- Rollback safety (release/deploy quan trọng): `Known Good Version → Backup/Checkpoint → Change → Validation → Rollback Plan`.
- Không tự thêm/bỏ tính năng, refactor, đổi kiến trúc/UI/schema/config production, đổi lịch sử git.
- Hoàn tất khi: mode xong đúng yêu cầu; validate xong; không còn lỗi nghiêm trọng đã biết; git/version hợp lệ; tài liệu và Map đã sync; với DEPLOY thì deploy đã được xác nhận thành công.

## Checklist
- [ ] Mỗi lệnh đã chạy đều có permission (L3); không thao tác git ghi ngoài yêu cầu (L4)
- [ ] High-Risk đã được xác nhận trước khi làm
- [ ] Không báo PASS cho thứ chưa chạy; phần chưa chạy ghi `NOT RUN` + lệnh
- [ ] Map/tài liệu/version đã sync

## Report mẫu
```text
Mode: <tên>   Project: <path>
Done: <việc đã làm>   Version/commit: <v / hash|không biết>
Verified: <T-level + kết quả thật>   NOT RUN: <lệnh cho user>
Status: <ổn | cảnh báo: ...>   Files changed: <...>
Risks / warnings: ...   Cleanup: none | LEFTOVER: ...
```
