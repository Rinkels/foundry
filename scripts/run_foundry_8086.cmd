@echo off
rem Foundry as infrastructure: the Atlas webhook receiver must be listening on
rem 8086 (the Cloudflare tunnel's origin) whenever GitHub pushes arrive, or the
rem deploy is silently lost. A Task Scheduler task runs this at logon and
rem restarts it on failure. --noreload: one process, no autoreloader child.
cd /d C:\Projects\foundry
if not exist "%LOCALAPPDATA%\Foundry" mkdir "%LOCALAPPDATA%\Foundry"
echo [%date% %time%] starting runserver 0.0.0.0:8086 >> "%LOCALAPPDATA%\Foundry\runserver.log"
C:\Python313\python.exe manage.py runserver 0.0.0.0:8086 --noreload >> "%LOCALAPPDATA%\Foundry\runserver.log" 2>&1
