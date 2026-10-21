# ARCHITECTURE — Link Vault

Phiên bản thiết kế 1.0 · Scale: Small · Python 3.11+ · PyQt6 · SQLite · Windows 10/11

## 1. Tổng quan

Link Vault là app desktop một người dùng để ghi link web kiếm tiền (MMO, AI, Airdrop), danh sách AI hỗ trợ công việc và ghi chú. Dữ liệu nằm ở **thư mục do người dùng chọn**, app không phụ thuộc đường dẫn cố định nào nên đóng gói PyInstaller onedir không phải sửa code.

Chuỗi thiết kế: REQUIREMENTS → UI_SPEC → workflow → kiến trúc → cấu trúc code.

## 2. Workflow chính

1. Khởi động: `paths` xác định thư mục app, `config` đọc `config.json`, mở DB trong `data_dir`.
2. Người dùng chọn tab ở sidebar, danh sách tải từ DB qua model.
3. Thêm, sửa, xoá qua hộp thoại, ghi DB rồi model cập nhật đúng dòng đó.
4. Cài đặt: đổi thư mục dữ liệu, nhập, xuất, giao diện.
5. Thoát: tự sao lưu (nếu bật) rồi đóng DB.

## 3. Data flow

```
UI (view/dialog) → controller-less signal/slot → EntryListModel / NoteModel
                                              → db.py (sqlite3, tham số hoá)
                                              → <data_dir>/linkvault.db
Nhập/xuất/chuyển dữ liệu/sao lưu → io_data.py chạy trong QThreadPool (kết nối DB riêng)
                                   → tiến trình và lỗi quay về UI bằng signal
```

## 4. Chiến lược đường dẫn (trọng tâm để đóng gói onedir)

Mọi đường dẫn chỉ được tạo trong `app/paths.py`. Module khác không dùng `__file__`, `os.getcwd()` hay chuỗi đường dẫn tự viết.

| Khái niệm | Cách xác định |
|---|---|
| `app_dir` | Đóng gói: `Path(sys.executable).parent`. Chạy mã nguồn: thư mục gốc dự án. Dựa vào `getattr(sys, "frozen", False)` |
| `resource_path(rel)` | Tài nguyên chỉ đọc (font, icon, qss). Đóng gói: `Path(sys._MEIPASS) / rel` (onedir là thư mục `_internal`). Chạy mã nguồn: gốc dự án / rel |
| `config_path` | Ưu tiên 1: `app_dir/config.json` nếu tồn tại (chế độ Di động). Ưu tiên 2: `%APPDATA%\LinkVault\config.json` (lấy từ biến môi trường, dự phòng `Path.home()`) |
| `data_dir` | Đọc từ `config.json`. Lưu **tương đối** so với `app_dir` nếu nằm trong đó (ví dụ `data`), ngược lại lưu tuyệt đối. Mặc định chế độ Di động: `app_dir/data`. Mặc định chế độ thường: `%APPDATA%\LinkVault\data` |

Quy tắc:
- DB chỉ lưu **tên file logo** (ví dụ `a1b2.png`); file nằm ở `data_dir/logos/`. Nhờ vậy chép nguyên thư mục dữ liệu sang máy khác vẫn chạy.
- `data_dir` thiếu hoặc không ghi được: hiện hộp thoại bắt người dùng chọn lại (báo lỗi rõ ràng, không tự chuyển sang thư mục khác trong im lặng).
- Đổi `data_dir` trong Cài đặt: kiểm tra ghi thử → (tuỳ chọn) chuyển `linkvault.db`, `logos/` bằng worker → đóng DB cũ, mở DB mới → ghi `config.json` bằng ghi nguyên tử (ghi file tạm rồi `os.replace`). Không cần khởi động lại.
- Mọi thao tác dùng `pathlib.Path`, ghi file với `encoding="utf-8"`.

## 5. Layer và module

| Layer | Module | Trách nhiệm |
|---|---|---|
| Entry | `main.py` | Tạo `QApplication`, nạp theme, mở DB, hiện cửa sổ chính |
| Core | `app/paths.py` | Xác định đường dẫn (mục 4) |
| Core | `app/config.py` | Đọc và ghi `config.json` nguyên tử: `data_dir`, `theme`, `auto_backup`, `window_geometry`, `last_tab` |
| Data | `app/db.py` | Kết nối SQLite (WAL, `foreign_keys=ON`), tạo bảng, migration theo `PRAGMA user_version`, CRUD, tìm kiếm, mọi câu SQL dùng tham số |
| Data | `app/models.py` | `Entry`, `Note` (dataclass); `EntryListModel`, `NoteListModel` (QAbstractListModel, tải theo lô 200 qua `canFetchMore`) |
| Data | `app/io_data.py` | Xuất JSON/CSV, nhập JSON/CSV (gộp hoặc ghi đè), chuyển thư mục dữ liệu, sao lưu; worker `QRunnable` |
| UI | `app/ui/theme.py` | Sinh QSS từ token trong `UI_SPEC.json` (sáng/tối), nạp font |
| UI | `app/ui/main_window.py` | Khung chính, sidebar, `QStackedWidget`, phím tắt, toast |
| UI | `app/ui/entry_view.py` | Tab MMO/AI: `QListView` + delegate vẽ dòng (logo, link, tiến độ, nhãn, note, nút Sửa/Xoá) |
| UI | `app/ui/card_view.py` | Tab Airdrop/Tool: `QListView` IconMode + delegate vẽ thẻ |
| UI | `app/ui/note_view.py` | Tab Note: danh sách + editor, tự lưu 800ms |
| UI | `app/ui/dialogs.py` | `EntryDialog` (thêm/sửa, kiểm tra dữ liệu), `ConfirmDialog` |
| UI | `app/ui/settings_view.py` | Thư mục dữ liệu, nhập xuất, giao diện, sao lưu |
| UI | `app/ui/widgets.py` | `TagEditor`, `ToastBar`, `LogoLabel`, tiện ích dùng chung |

Phụ thuộc một chiều: `ui → models/io_data → db → config → paths`. `db` không import PyQt.

## 6. Mô hình dữ liệu (SQLite, `linkvault.db`)

```
entries(id INTEGER PK, kind TEXT NOT NULL CHECK(kind IN ('mmo','ai','airdrop','tool')),
        name TEXT NOT NULL, logo TEXT, link TEXT, how_to TEXT,
        progress INTEGER DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
        tools TEXT DEFAULT '[]',   -- mảng JSON các nhãn
        note TEXT, status TEXT, effect TEXT,
        sort_order INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT)
notes(id INTEGER PK, title TEXT NOT NULL, body TEXT, pinned INTEGER DEFAULT 0,
      created_at TEXT, updated_at TEXT)
INDEX idx_entries_kind_sort ON entries(kind, sort_order)
INDEX idx_entries_kind_status ON entries(kind, status)
```

Một bảng `entries` dùng chung cho 4 tab, trường nào không dùng thì để trống (MMO/AI dùng how_to, progress, tools, note; Airdrop dùng status, note; Tool dùng link, effect). Thêm trường mới chỉ cần migration tăng `user_version`.

## 7. Nhập và xuất

- **JSON** (sao lưu đầy đủ): `{"app":"LinkVault","format_version":1,"exported_at":"...","entries":[...],"notes":[...]}`; logo nhúng base64 (đã thu nhỏ 96×96) để khôi phục được khi sang máy khác.
- **CSV** (tab hiện tại): UTF-8 có BOM, một dòng một bản ghi, cột `tools` ngăn cách bằng `;`.
- **Nhập**: kiểm tra `format_version`, từng dòng được validate; dòng lỗi được liệt kê trong báo cáo, không bỏ qua im lặng.
  - *Gộp*: khớp theo `(kind, tên không phân biệt hoa thường, link)`; trùng thì giữ bản có `updated_at` mới hơn.
  - *Ghi đè*: tự sao lưu trước, sau đó thay toàn bộ dữ liệu; cần xác nhận rõ.

## 8. Hiệu năng

- Danh sách dùng model/view + delegate tự vẽ: số widget không tăng theo số dòng, cuộn mượt với hàng nghìn bản ghi.
- Logo nạp lười, cache `QPixmap` có giới hạn (LRU 256) ở kích thước hiển thị.
- Tìm kiếm debounce 200ms, truy vấn có chỉ mục theo `kind`.
- SQLite WAL + commit theo lô khi nhập; thao tác nặng chạy ở `QThreadPool`, UI chỉ nhận signal tiến độ.
- Không polling, không timer nền ngoài timer tự lưu của Note.

## 9. Xử lý lỗi và bảo mật

- Không nuốt lỗi: lỗi DB, file, nhập xuất được ghi log (`app.log` cạnh `config.json`) và hiện toast hoặc hộp thoại bằng ngôn ngữ dễ hiểu.
- Link chỉ mở khi bắt đầu bằng `http://` hoặc `https://` (qua `QDesktopServices.openUrl`).
- SQL luôn dùng tham số; đường dẫn logo luôn là tên file, không nhận đường dẫn tuỳ ý từ file nhập (chặn path traversal).
- Không có mạng, không có secret.

## 10. Cấu trúc thư mục

```
LinkVault/
├─ main.py
├─ app/
│  ├─ __init__.py  paths.py  config.py  db.py  models.py  io_data.py
│  └─ ui/  theme.py  main_window.py  entry_view.py  card_view.py
│          note_view.py  dialogs.py  settings_view.py  widgets.py
├─ assets/  fonts/  icons/
├─ tests/  test_paths.py  test_db.py  test_io_data.py
├─ linkvault.spec          (PyInstaller onedir)
├─ requirements.txt  requirements-dev.txt
├─ REQUIREMENTS.json  UI_SPEC.json  ARCHITECTURE.md  PROJECT_MAP.json
├─ UI_PREVIEW.html  ui_images/
└─ PROGRESS.md             (tạo ở Phase 2)
```

## 11. Dependency

| Tên | Dùng khi | Lý do |
|---|---|---|
| PyQt6 | chạy | Khung giao diện đã chọn |
| sqlite3, json, csv, pathlib, logging | chạy | Thư viện chuẩn, đủ dùng, không thêm gói ngoài |
| PyInstaller | build | Đóng gói onedir |
| pytest | dev | Kiểm thử `paths`, `db`, `io_data` (không cần UI) |

## 12. Đóng gói onedir

- Lệnh dự kiến: `pyinstaller linkvault.spec` (chế độ onedir, `console=False`). Spec khai báo `datas` cho `assets/`.
- Kết quả: `dist/LinkVault/LinkVault.exe` + `_internal/`. Chạy được ở bất kỳ thư mục nào vì mọi đường dẫn đi qua `paths.py`.
- Chế độ Di động: tạo file `config.json` cạnh exe (Cài đặt tự tạo khi chọn Di động) → mang cả thư mục `dist/LinkVault` đi là mang luôn dữ liệu.

## 13. Quyết định kỹ thuật

| Quyết định | Lý do | Đổi lại |
|---|---|---|
| SQLite thay vì JSON | Tìm kiếm nhanh, ghi nguyên tử, không đọc lại cả file mỗi lần lưu | File nhị phân, bù bằng xuất JSON/CSV |
| Delegate tự vẽ thay widget từng dòng | Mượt khi dữ liệu nhiều | Code vẽ dài hơn, nhưng gom trong 2 module |
| Một bảng `entries` cho 4 tab | Ít module, nhập xuất đơn giản | Có cột để trống theo tab |
| Không có controller riêng | Quy mô Small, signal/slot giữa view và model là đủ | Nếu lớn lên sẽ tách |
| Logo copy vào `data_dir/logos` | Dữ liệu tự chứa, di chuyển dễ | Tốn thêm ít dung lượng |

## 14. Quy tắc tổ chức code

- Đường dẫn chỉ ở `paths.py`; câu SQL chỉ ở `db.py`; UI không chứa logic nghiệp vụ.
- Mỗi file một trách nhiệm, giữ dưới khoảng 300 dòng.
- Màu và cỡ chữ lấy từ `theme.py` (token trong `UI_SPEC.json`), không rải mã màu trong view.
- Tên định danh, comment, commit viết tiếng Anh; chữ hiển thị cho người dùng bằng tiếng Việt.
