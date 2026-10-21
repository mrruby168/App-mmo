# WORKFLOW — REFACTOR (chỉ khi user yêu cầu)

Áp dụng thêm `01_core.md` §16. Refactor KHÔNG đổi hành vi và KHÔNG trộn với feature/fix.

## Khi tự thấy code nên refactor mà user chưa yêu cầu
Không làm. Báo vị trí, lý do ngắn, phạm vi ảnh hưởng, rồi Question hỏi có cho phép không. Chỉ làm sau khi user đồng ý.

## Các bước
**B1 — Phạm vi:** chốt chính xác file/hàm cần refactor và mục tiêu (dễ đọc hơn? bớt trùng?). Đọc Map (nếu có) + Read source thật.

**B2 — Baseline hành vi:** có test thì chạy (qua L3) ghi kết quả; chưa có test thì ghi baseline T2 (kịch bản + kết quả hiện tại). Không chạy được: ghi rõ `baseline NOT RUN` là rủi ro lớn và hỏi user có tiếp tục không.

**B3 — Plan:** TodoWrite, các bước nhỏ, mỗi bước độc lập kiểm chứng được.

**B4 — Làm từng bước nhỏ bằng Edit:**
- Đổi tên: Grep MỌI chỗ dùng trước, sửa từng chỗ bằng Edit, Grep lại xác nhận không còn tên cũ.
- Di chuyển/tách file chỉ khi nằm trong kế hoạch; cập nhật Map.
- Không đổi format/tên hàng loạt ngoài phạm vi.
- Sau mỗi bước: Read-back + verify (`01_core.md` §5).

**B5 — So sánh với baseline:** hành vi phải giống hệt. Khác thì hoàn tác phần đó (hoặc nhắc user `/undo`) và tìm nguyên nhân.

**B6 — Sync + dọn:** `PROJECT_MAP.json` nếu cấu trúc đổi; `ARCHITECTURE.md` nếu trách nhiệm module đổi. Dọn theo §6. Append 1 entry `PROGRESS.md` (§21) khi xong.

## Checklist
- [ ] Hành vi không đổi (có bằng chứng, hoặc `NOT RUN` được nói rõ)
- [ ] Không lẫn feature/fix; không sửa ngoài phạm vi
- [ ] Không còn tham chiếu tên cũ; Map đã sync

## Report mẫu
```text
Refactor: <mục tiêu> — phạm vi: <file/hàm>
Baseline: <test/T2 trước> → Sau: <kết quả> (khớp: có/không/NOT RUN)
Changed: <file:range ...>   Sync: PROJECT_MAP.json <updated|N/A>
Risks: ...   Cleanup: none | LEFTOVER: ...   (hoàn tác: /undo)
```
