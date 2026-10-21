# ROUTER — chọn đúng 1 workflow theo intent

Thứ tự ưu tiên khi xung đột: xem `01_core.md` §0.

## 1. Load protocol
`01_core.md` và `router.md` đã tự nạp qua `opencode.json`. Việc của bạn:
1. Phân loại intent (bảng §3) hoặc kiểm tra task nhỏ (§2).
2. Read ĐÚNG 1 file workflow được chọn, đọc hết trước khi hành động.
3. Mở đầu reply bằng: `Rules loaded: CORE + router + <workflows/x.md | SKIP-small>`.

Workflow bảo "đọc file X" thì chỉ đọc X ở bước đó. Cấm đọc trước workflow khác, cấm Glob-rồi-đọc cả thư mục `rules\workflows`.

## 2. Task NHỎ → SKIP workflow và Design Pack
**Nhỏ** = đồng thời thỏa: sửa 1 file; ≤ ~2 dòng logic hoặc chỉ text/CSS lặt vặt; không tạo/xóa file; không đổi logic nghiệp vụ, data, API, schema, dependency, cấu trúc.

Quy trình:
1. Read file liên quan (Grep nếu cần định vị).
2. Edit tối thiểu (`01_core.md` §4).
3. Verify theo `01_core.md` §5: Read-back + T1 nếu được phép.
4. Report 3 dòng: Changed / Verified (hoặc NOT RUN) / Risks.

Không đọc `REQUIREMENTS.json`, `UI_SPEC.json`, `ARCHITECTURE.md`, `PROJECT_MAP.json`. Không TodoWrite. LOCK và HARD vẫn áp dụng đầy đủ.

**Leo thang:** đang làm mà thấy phải đụng >1 file logic, cần file mới, hoặc đổi hành vi thì dừng, báo 1 dòng và chuyển sang `feature.md` hoặc `fix.md`. Không chắc nhỏ hay không thì coi là KHÔNG nhỏ.

## 3. Bảng router

| Intent của user | Load đúng 1 file | Mode OpenCode |
|---|---|---|
| App mới từ ý tưởng / chưa có dự án | `workflows/new_app.md` (Phase 1 DESIGN → user duyệt → Phase 2 BUILD) | Question ở Plan được; ghi file cần Build |
| Chỉ thiết kế (form, UI, kiến trúc) | `workflows/new_app.md` (chỉ Phase 1) | như trên |
| Code từ Design Pack đã duyệt | `workflows/new_app.md` (chỉ Phase 2) | Build |
| Thêm tính năng / đổi hành vi trong dự án có sẵn | `workflows/feature.md` | Build |
| Sửa bug / lỗi | `workflows/fix.md` | Build |
| Review code, không sửa | `workflows/review.md` | **Plan** |
| Refactor | `workflows/refactor.md` | Build |
| Đọc toàn bộ source để tạo/tạo lại `ARCHITECTURE.md` + `PROJECT_MAP.json` | `workflows/audit.md` | Plan để đọc, Build để ghi 2 file |
| Git, version, dependency, build, test, release, deploy, backup, rollback, status, sync, audit quản lý dự án | `workflows/release.md` | Build |

- **Hỗn hợp:** TodoWrite chia thành các bước có thứ tự; mỗi bước theo workflow riêng, chỉ đọc file workflow của bước đó khi tới bước đó.
- **Không rõ intent:** 1 Question duy nhất.
- **Task thay đổi nhưng dự án không có `PROJECT_MAP.json`:** theo Case 2 của `feature.md`/`fix.md`; làm xong đề nghị `audit.md`.

## 3b. Kickoff kênh approve (chỉ workflow Build-type)

Sau khi chọn workflow, hỏi user 1 câu duy nhất: kênh approve **PC hay ĐT** (Question, 2 options). Ghi đáp án vào mục TodoWrite đầu tiên.
- **PC:** code và hỏi trực tiếp trong phiên như mặc định.
- **ĐT:** bật cổng tele — chạy checklist health `01_core.md` §19 trước khi code: serve sống? bot online? project bot trùng project code? Fail mục nào thì dừng báo user, không code mò.
- **Không trả lời được** (giao việc rồi đi luôn): mặc định **PC** — mọi quyền chờ, việc chạy tới đâu hay tới đó, phần còn lại dồn `NOT RUN`. Không tự bật cổng tele khi chưa được chọn.

## 4. Scale và Design Pack (chỉ dùng cho `new_app.md`)
AI **đề xuất** scale từ tín hiệu (số tính năng, vai trò, cần DB/API/auth, tích hợp); user xác nhận. LOC chỉ để tham khảo: Small < 3.000 · Medium 3.000–10.000 · Large > 10.000.

| Artefact | Small | Medium | Large |
|---|---|---|---|
| `REQUIREMENTS.json` | Bắt buộc | Bắt buộc | Bắt buộc |
| `UI_SPEC.json` + `UI_PREVIEW.html` | Nếu có UI | Nếu có UI | Nếu có UI |
| `ARCHITECTURE.md` | Bắt buộc (ngắn) | Bắt buộc | Bắt buộc + quyết định kỹ thuật + rủi ro |
| `PROJECT_MAP.json` | Bắt buộc | Bắt buộc | Bắt buộc |
| `PROJECT_BLUEPRINT.mmd` | Tùy chọn | Bắt buộc | Bắt buộc |

Không có UI (API, CLI, library, bot, service): bỏ `UI_SPEC.json` và `UI_PREVIEW.html`.

## 5. Ngôn ngữ
- Trả lời theo ngôn ngữ user đang viết. Câu hỏi/form cho user cũng vậy.
- Identifier, code, comment, commit message, key JSON: tiếng Anh (trừ khi dự án đã có quy ước khác).
- Tài liệu như `ARCHITECTURE.md`: theo "document language" chọn trong Form (mặc định: ngôn ngữ user).

## 6. Glossary
| Thuật ngữ | Nghĩa |
|---|---|
| **Design Pack** | Bộ artefact thiết kế ở bảng §4. |
| **Planned / Actual Map** | `PROJECT_MAP.json` với `map_type: "planned"` (trước khi code) hoặc `"actual"` (khớp code thật). |
| **WI** | Work item trong build workflow (WI-1, WI-2...). Dùng "WI" để khỏi nhầm với tool `Task`. Trạng thái: `PENDING`, `CODING`, `TESTING`, `BLOCKED`, `DONE` (ghi bằng prefix trong TodoWrite). |
| **T1 / T2 / T3** | Mức test, định nghĩa ở `01_core.md` §14. |
| **Stub** | Placeholder tạm, theo `01_core.md` §8. |
| **High-Risk** | Danh sách ở `01_core.md` §17. |
| **PROGRESS.md** | Checkpoint append-only ở root dự án (`01_core.md` §21): ghi sau mỗi WI, đọc 10 mục cuối khi resume phiên. |

Ví dụ áp dụng end-to-end (chỉ đọc khi chưa rõ cách làm): `examples/add_button_html.md`.
