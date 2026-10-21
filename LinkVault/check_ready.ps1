# LinkVault - Kiem tra du file de push GitHub + build EXE
# Chay: powershell -ExecutionPolicy Bypass -File .\check_ready.ps1
$ErrorActionPreference = 'SilentlyContinue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
Write-Host "== THU MUC goc: $root ==" -ForegroundColor Cyan

# 1. File bat buoc
$required = @(
  'main.py','build_exe.py','requirements.txt','requirements-dev.txt',
  'config.json','UI_SPEC.json',
  'app\__init__.py','app\paths.py','app\db.py','app\models.py','app\io_data.py','app\config.py',
  'app\ui\__init__.py','app\ui\theme.py','app\ui\widgets.py','app\ui\imaging.py',
  'app\ui\main_window.py','app\ui\entry_view.py','app\ui\card_view.py',
  'app\ui\note_view.py','app\ui\settings_view.py','app\ui\dialogs.py'
)
$missing = @()
foreach ($f in $required) { if (-not (Test-Path $f)) { $missing += $f } }
if ($missing.Count -eq 0) { Write-Host "[OK] Du $($required.Count) file nguon Python/config." -ForegroundColor Green }
else { Write-Host "[THIEU] $($missing -join ', ')" -ForegroundColor Red }

# 2. Workflow GitHub Actions (nam TREN app\ui, o goc repo cha cua LinkVault)
$wfCandidates = @((Join-Path $root '..\.github\workflows\build-windows.yml'), (Join-Path $root '.github\workflows\build-windows.yml'))
$wf = $wfCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($wf) { Write-Host "[OK] Workflow: $wf" -ForegroundColor Green }
else { Write-Host "[CHU Y] Khong thay .github\workflows\build-windows.yml -> Actions se KHONG tu build.`n        Copy thu muc .github vao goc repo khi push." -ForegroundColor Yellow }

# 3. Check 3 patch da ap dung chua
$p1 = Select-String -Path 'app\ui\note_view.py'    -Pattern 'setTabChangesFocus\(True\)'      -Quiet
$p2 = Select-String -Path 'app\ui\main_window.py'  -Pattern 'hasattr\(view, "count_changed"\)' -Quiet
Write-Host "--- Patch ---" -ForegroundColor Cyan
if ($p1) { Write-Host '[OK] note_view.py : setTabChangesFocus' -ForegroundColor Green } else { Write-Host '[LOI] note_view.py van dung tabChangesFocus(True) -> sua lai' -ForegroundColor Red }
if ($p2) { Write-Host '[OK] main_window.py : hasattr guard cho SettingsView' -ForegroundColor Green } else { Write-Host '[LOI] main_window.py chua co hasattr guard -> loi count_changed' -ForegroundColor Red }

# 4. Git / remote
Write-Host "--- Git ---" -ForegroundColor Cyan
if (Test-Path (Join-Path $root '..\.git')) {
  Push-Location (Join-Path $root '..')
  $rem = git remote get-url origin 2>$null
  if ($rem) { Write-Host "[OK] Remote origin: $rem" -ForegroundColor Green }
  else { Write-Host '[CHUA] Chua co remote origin -> gan remote add origin roi push' -ForegroundColor Yellow }
  Pop-Location
} else { Write-Host '[CHUA] Thu muc cha chua phai la git repo -> git init tru khi push' -ForegroundColor Yellow }

# 5. Artifact can loai tru khi commit
Write-Host "--- Ve sinh repo ---" -ForegroundColor Cyan
$junk = @('build','dist','__pycache__','*.spec','app.log','.venv') | Where-Object { Test-Path $_ }
if ($junk.Count -gt 0) { Write-Host "[LOAI TRU] Khong commit: $($junk -join ', ') (kiem tra .gitignore)" -ForegroundColor Yellow }
else { Write-Host '[OK] Khong co artifact build trong thu muc source.' -ForegroundColor Green }

Write-Host "`nKet luan: neu khong co dong [THIEU]/[LOI] mau do -> day len GitHub du dieu kien build." -ForegroundColor Cyan
