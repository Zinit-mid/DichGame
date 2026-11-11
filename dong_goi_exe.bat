@echo off
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py
echo [1/3] Cai thu vien va cong cu dong goi...
%PY% -m pip install -r requirements.txt pyinstaller
for /f "usebackq delims=" %%p in ("requirements_them.txt") do %PY% -m pip install %%p
echo [2/3] Dong goi DichGame.exe (mat 1-3 phut)...
%PY% -m PyInstaller --noconfirm --onefile --noconsole --name DichGame --icon icon.ico --add-data "icon.ico;." --collect-all winocr --collect-all winrt --collect-all windows_capture --collect-all bettercam --collect-all dxcam --collect-all comtypes --collect-all ctranslate2 --collect-all sentencepiece --collect-all edge_tts --collect-all pycaw dich_game.py
if errorlevel 1 (
  echo Dong goi bi loi. Chup man hinh cua so nay gui nguoi viet app.
  pause
  exit /b 1
)
echo [3/3] Tao goi phat hanh...
if not exist phat_hanh mkdir phat_hanh
copy /y dist\DichGame.exe phat_hanh\DichGame.exe >nul
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dich_game.py','icon.ico','requirements.txt','requirements_them.txt','chay_thu.bat','dong_goi_exe.bat','HUONG_DAN.txt' -DestinationPath 'phat_hanh\DichGame.zip'"
echo.
echo Xong! App hoan chinh: phat_hanh\DichGame.exe
explorer phat_hanh
pause
