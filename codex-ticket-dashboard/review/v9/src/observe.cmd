@echo off
"%~1" -I -B -m codex_ticket_dashboard.lifecycle.command --config "%~2" --source-host "%~3" --source-kind "%~4"
if not "%ERRORLEVEL%"=="0" exit /b 1
exit /b 0
