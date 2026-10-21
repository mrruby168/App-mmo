# AGENTS.md — RULE-OPENCODE v1.0.1

Bạn là AI-AGENT chạy trong OpenCode (Windows, PowerShell 5.1). Tool duy nhất bạn có: Read, Edit, Write, Glob, Grep, Bash, WebFetch, WebSearch, Task, TodoWrite, Question, Skill.

**Scope khóa: chỉ task CODE. Không thêm workflow mới khi user chưa duyệt.**

## Load protocol (theo thứ tự)
1. `rules/01_core.md` — luôn có trong context (nạp qua `opencode.json`); chưa thấy thì Read.
2. `rules/router.md` — phân loại intent, chọn đúng 1 workflow (hoặc SKIP nếu task nhỏ).
3. Read đúng 1 file `rules/workflows/<tên>.md` mà router chọn. Cấm đọc trước workflow khác.
4. Dòng đầu reply đầu tiên: `Rules loaded: CORE + router + <workflows/x.md | SKIP-small>`.

## LOCK — đứng trên mọi thứ (chi tiết: `rules/01_core.md` §1)
- Chỉ đọc/sửa trong `D:\AI-AGENT`; ngoài đó hỏi user từng lần.
- Tuyệt đối không đụng `D:\AI-AGENT\OPENCODE` (kể cả Read/Glob/Grep).
- Không chạy Bash/script khi user chưa cho phép explicitly (hiển thị lệnh nguyên văn rồi hỏi).
- Không commit/push/PR khi user chưa yêu cầu rõ.

## Golden rules
1. Read trước khi viết. Không bịa API, hàm, flag, đường dẫn.
2. Sửa file có sẵn bằng Edit; Glob + Grep trước mọi Write. Không tạo bản `_new`/`_v2`/`.bak`.
3. Verify bằng chạy thật khi được phép; không chạy được thì ghi `NOT RUN` + đưa lệnh. Không suy diễn rồi báo "đã test".
4. Thay đổi nhỏ nhất mà đúng. Không sửa lan.
5. Không để rác: debug code, file test tạm, code comment-out.
6. Không hardcode/log/commit secret. Không nuốt lỗi.
7. Tìm root cause trước khi fix. Hai fix liên tiếp thất bại thì dừng lại xem xét lại.
8. Task ≥3 bước dùng TodoWrite; codebase lớn dùng Task (explore); tool độc lập gọi song song.
9. Giữ `PROJECT_MAP.json` (và `ARCHITECTURE.md` khi thiết kế đổi) khớp code thật.
10. Báo cáo ngắn (Changed / Verified / Assumptions / Risks) rồi DỪNG.

Cấu hình: `opencode.json` (cùng thư mục) nạp `rules/01_core.md + rules/router.md` qua "instructions"; workflow đọc lười khi router chọn. Không sửa các file rule này trừ khi user yêu cầu đích danh.
