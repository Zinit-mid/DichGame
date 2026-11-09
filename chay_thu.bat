@echo off
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py
echo Dang cai thu vien chinh (lan dau hoi lau)...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Khong cai duoc thu vien chinh. Kiem tra Python va ket noi mang.
  pause
  exit /b 1
)
echo Dang cai thu vien chup man hinh game (loi o buoc nay cung khong sao)...
for /f "usebackq delims=" %%p in ("requirements_them.txt") do %PY% -m pip install %%p
echo Dang mo app...
%PY% dich_game.py
pause
