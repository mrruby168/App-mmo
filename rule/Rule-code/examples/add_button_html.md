# VÍ DỤ END-TO-END — "Thêm 1 nút vào app HTML"

Chỉ là ví dụ minh họa cách áp dụng bộ rule; không phải rule. Dự án giả định: `D:\AI-AGENT\CODE\todo-app\` gồm `index.html`, `app.js`, `style.css`, `PROJECT_MAP.json`, `ARCHITECTURE.md`, thư mục `.git`.

**Yêu cầu của user:** "Thêm nút 'Xóa việc đã xong' vào app todo, bấm vào thì xóa các việc đã hoàn thành."

## 1. Router chọn gì
- Task nhỏ? KHÔNG: thêm element + logic mới, chạm 2 file. → Intent "thêm tính năng" → `workflows/feature.md`. Mode: Build.
- `01_core.md` và `router.md` đã nạp sẵn qua `opencode.json`; Read `rules/workflows/feature.md`.
- Reply mở đầu: `Rules loaded: CORE + router + workflows/feature.md`.

## 2. Thứ tự đọc file
1. `rules/workflows/feature.md`.
2. `D:\AI-AGENT\CODE\todo-app\PROJECT_MAP.json`, rồi `ARCHITECTURE.md`.
3. Freshness: Read `.git\HEAD` → Read file ref → so hash với `git_commit` của Map (lệch thì ghi "Map stale", coi Map là gợi ý).
4. Song song 1 lượt: Grep `render|saveTodos|todos|btn` trong `todo-app\`; Read `index.html`; Read `app.js`. `style.css` chỉ Read nếu cần class mới.
5. Không Read `D:\AI-AGENT\OPENCODE`, không Glob/Grep từ `D:\AI-AGENT` gốc.

## 3. TodoWrite
`1 Định vị + đọc` · `2 Thêm button + handler` · `3 VERIFY` · `4 CLEANUP + REPORT`.

## 4. Acceptance criteria (đưa user xem, không cần Question vì đã rõ)
- Có nút `Xóa việc đã xong` trong trang.
- Bấm nút: các item `done` bị xóa, item chưa xong còn nguyên, danh sách render lại và lưu lại.

## 5. Diff chạm gì
| File | Thay đổi |
|---|---|
| `index.html` | +1 dòng: `<button id="clear-completed" class="btn">Xóa việc đã xong</button>` |
| `app.js` | +1 hàm `clearCompleted()` (~6 dòng, tái dùng `render()` và `saveTodos()` đã Grep xác nhận tồn tại) + 1 dòng `addEventListener` |
| `PROJECT_MAP.json` | Thêm symbol `clearCompleted` vào module `app.js` |
| `ARCHITECTURE.md` | Không đổi (không có module/data flow mới) |
| `style.css` | Không đổi (tái dùng class `.btn` có sẵn) |

Tất cả bằng Edit. Không tạo file mới. Không chạm `.git\`, không chạm ngoài `todo-app\`.

## 6. Verify
1. **Read-back** vùng đã sửa của `index.html` và `app.js`. [VERIFIED]
2. **Grep chéo:** `clear-completed` xuất hiện đúng 1 lần trong `index.html` và 1 lần trong `app.js`; không còn `console.log` do mình thêm. [VERIFIED]
3. **T1 (cần permission):** Question hiển thị: lệnh `node --check 'D:\AI-AGENT\CODE\todo-app\app.js'`; mục đích: kiểm cú pháp; tác động: không ghi file, không dùng mạng, không chạy nền. Options: "Cho chạy" / "Không".
   - Cho chạy → chạy, đọc exit code + output thật. Exit 0 → `T1: syntax OK`. Lỗi `node` không tồn tại → báo nguyên văn lỗi, không bịa.
   - Không → `T1 NOT RUN`, kèm lệnh cho user.
4. **T2:** cần mở trình duyệt nên không tự chạy → `NOT RUN`, đưa các bước cho user (bên dưới).
5. Không tạo file test tạm → không có gì cần dọn.

## 7. Report mẫu
```text
Feature: nút "Xóa việc đã xong" — acceptance: nút hiển thị (Read-back OK) | xóa item done + lưu (NOT RUN, T2)
Changed:
- todo-app\index.html:18 — thêm <button id="clear-completed">
- todo-app\app.js:54-60,71 — thêm clearCompleted() và đăng ký listener
- todo-app\PROJECT_MAP.json — thêm symbol clearCompleted cho app.js
Verified: Read-back + Grep chéo [VERIFIED]; T1 `node --check` exit 0 (user cho phép) 
NOT RUN: T2. Cho user: mở todo-app\index.html → thêm 3 việc, đánh dấu 2 việc xong → bấm "Xóa việc đã xong"
  → kỳ vọng: còn đúng 1 việc chưa xong; tải lại trang vẫn chỉ còn 1 việc.
Assumptions: app lưu todos qua saveTodos() như Grep thấy (không đổi định dạng lưu).
Risks: không.   Out-of-scope: app.js:30 có catch rỗng (có sẵn từ trước, chỉ báo, không sửa).
Sync: PROJECT_MAP.json updated; ARCHITECTURE.md N/A (không đổi module/data flow)
Cleanup: none
Tip: /undo hoàn tác lượt sửa này.
```
