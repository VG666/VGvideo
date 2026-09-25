@echo off
rem ============================================================================
rem  VG video - Nuitka standalone build script
rem
rem  Usage:  set VG_NAME / VG_DESC first if you want a Chinese exe name,
rem          then run this script.  (Defaults are ASCII so it always works.)
rem
rem  Notes (why these flags are required):
rem    1) Nuitka does NOT set sys.frozen, so model/paths.py takes the source
rem       branch and dirname(dirname(__file__)) resolves to the dist folder.
rem       Verified at runtime: config/ and Recordset/ are created in the dist.
rem    2) videovlc MUST use --include-raw-dir: --include-data-dir silently
rem       skips .dll (303 of 519 VLC files) and the package then depends on a
rem       system installed VLC.
rem    3) ckey.wasm / tx.js inside tx_server/vgplay are runtime data, not code:
rem       --include-data-dir=tx_server=tx_server carries them. The client keeps no copy
rem       (model/api is HTTP-only now), so there is nothing else to add.
rem    4) utility/aria2c.exe and utility/ffmpeg.exe travel as data files.
rem       test/ and Recordset/ are runtime/self-test only and are not packaged.
rem ============================================================================
setlocal
cd /d "%~dp0"

if "%VG_NAME%"=="" set VG_NAME=VGVideo
if "%VG_DESC%"=="" set VG_DESC=VG Video desktop client

set PYTHONPATH=%~dp0utility

python -m nuitka ^
  --standalone ^
  --assume-yes-for-downloads ^
  --jobs=4 ^
  --low-memory ^
  --enable-plugin=tk-inter ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico=ico/logo.ico ^
  --output-dir=build_nuitka ^
  --output-filename=%VG_NAME%.exe ^
  --include-data-dir=ico=ico ^
  --include-data-dir=rotation_local=rotation_local ^
  --include-raw-dir=videovlc=videovlc ^
  --include-data-dir=config=config ^
  --include-data-dir=tx_server=tx_server ^
  --include-data-files=utility/aria2c.exe=utility/aria2c.exe ^
  --include-data-files=utility/ffmpeg.exe=utility/ffmpeg.exe ^
  --include-module=vlc ^
  --include-module=max_win ^
  --include-module=windnd ^
  --include-module=ToolTips ^
  --company-name=VGVideo ^
  --product-name=%VG_NAME% ^
  --file-description="%VG_DESC%" ^
  --file-version=1.0.0.0 ^
  --product-version=1.0.0.0 ^
  main.py > "%~dp0_build_log.txt" 2>&1

set RC=%ERRORLEVEL%
echo.
echo [Nuitka exit code] %RC%
findstr /C:"Successfully created" /C:"FATAL" /C:"ERROR" /C:"Error" "%~dp0_build_log.txt"

endlocal
