@echo off
REM Windows Task Scheduler example:
REM - Create a basic task to run this .cmd every 15 minutes.
REM - Start in: path\to\your\repo

setlocal
cd /d %~dp0\..

REM If using venv:
IF EXIST .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
)

python tools\update_home_data.py
endlocal
