"""Build Link Vault thành file .exe (PyInstaller --onedir) để tải về máy dùng.

Cách dùng (trên Windows, trong thư mục LinkVault):
    py -3.12 build_exe.py            # build thường (có console log)
    py -3.12 build_exe.py --clean    # xoá cache/build cũ rồi build lại
    py -3.12 build_exe.py --nozip    # build nhưng không đóng gói zip

Kết quả:
    dist/LinkVault/LinkVault.exe     -> thư mục ứng dụng (onedir)
    dist/LinkVault-windows.zip       -> nén toàn bộ dist/LinkVault để tải về

Trên Linux/macOS script vẫn chạy được để kiểm tra, nhưng chỉ tạo exe khi
có PyInstaller trên Windows (PyInstaller không cross-compile được).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Ensure Windows CI console can print UTF-8 output safely.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


ROOT = Path(__file__).resolve().parent

APP_NAME = "LinkVault"
ENTRY = ROOT / "main.py"
ICON = ROOT / "assets" / "icons" / "app_icon.ico"   # tuỳ chọn, bỏ qua nếu thiếu

# Tài nguyên nhúng vào bundle (_internal) — read-only, khớp app/paths.py
DATAS = [
    (ROOT / "UI_SPEC.json", "."),
    (ROOT / "assets/fonts", "assets/fonts"),
    (ROOT / "assets/icons", "assets/icons"),
]

HIDDEN_IMPORTS = [
    "app",
    "app.config",
    "app.paths",
    "app.db",
    "app.models",
    "app.io_data",
    "app.ui",
    "app.ui.theme",
    "app.ui.main_window",
    "app.ui.entry_view",
    "app.ui.card_view",
    "app.ui.note_view",
    "app.ui.dialogs",
    "app.ui.settings_view",
    "app.ui.widgets",
    "app.ui.imaging",
]


def _run(cmd: list[str]) -> None:
    print("+ " + " ".join(str(c) for c in cmd), flush=True)
    subprocess.check_call([str(c) for c in cmd])


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
        return
    except ImportError:
        print("PyInstaller chưa có -> cài đặt ...")
    _run([sys.executable, "-m", "pip", "install", "-r",
          str(ROOT / "requirements-dev.txt")])


def build(noconsole: bool = False) -> Path:
    if not ENTRY.is_file():
        sys.exit(f"Không tìm thấy entry point: {ENTRY}")

    add_data = []
    for src, dst in DATAS:
        if not Path(src).exists():
            print(f"Bỏ qua datas '{src}' (không tồn tại)")
            continue
        if Path(src).is_dir() and not any(Path(src).rglob("*")):
            print(f"Bỏ qua datas '{src}' (thư mục rỗng)")
            continue
        add_data += ["--add-data", f"{src}{os_sep()}{dst}"]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name", APP_NAME,
        *([] if noconsole else ["--console"]),
        *(["--windowed"] if noconsole else []),
        *([f"--icon={ICON}"] if ICON.is_file() else []),
        *add_data,
        *[f"--hidden-import={m}" for m in HIDDEN_IMPORTS],
        "--exclude-module", "tkinter",
        str(ENTRY),
    ]
    _run(cmd)

    out_dir = ROOT / "dist" / APP_NAME
    exe = out_dir / (APP_NAME + (".exe" if os.name == "nt" else ""))
    if not out_dir.is_dir():
        sys.exit("Build thất bại: không thấy dist/LinkVault")
    print(f"\nĐã build: {out_dir}")
    if exe.is_file():
        print(f"Executable: {exe}")
    return out_dir


def os_sep() -> str:
    return ";" if os.name == "nt" else ":"


def make_zip(out_dir: Path) -> Path:
    zip_path = ROOT / "dist" / f"{APP_NAME}-windows.zip"
    print(f"Nén {out_dir} -> {zip_path}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in out_dir.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(out_dir.parent))
    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"Xong: {zip_path} ({size_mb:.1f} MB)")
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", action="store_true",
                        help="Xoá build/, dist/, *.spec trước khi build.")
    parser.add_argument("--nozip", action="store_true",
                        help="Không tạo file zip sau khi build.")
    parser.add_argument("--noconsole", action="store_true",
                        help="Windowed mode (ẩn cửa sổ console).")
    args = parser.parse_args()

    if args.clean:
        for name in ("build", "dist"):
            shutil.rmtree(ROOT / name, ignore_errors=True)
        for spec in ROOT.glob(f"{APP_NAME}.spec"):
            spec.unlink()

    _ensure_pyinstaller()
    out_dir = build(noconsole=args.noconsole)
    if not args.nozip:
        make_zip(out_dir)

    print("""
Hướng dẫn sử dụng:
  1. Tải file dist/LinkVault-windows.zip về máy.
  2. Giải nén toàn bộ thư mục LinkVault (KHÔNG lấy riêng file .exe).
  3. Chạy LinkVault.exe. Dữ liệu mặc định lưu ở <APPDATA>/LinkVault,
     chạy với tham số --portable để dữ liệu nằm cạnh file exe.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
