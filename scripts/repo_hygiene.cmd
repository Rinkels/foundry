@echo off
rem Weekly repo-hygiene check (Task Scheduler). Writes
rem %LOCALAPPDATA%\Foundry\repo_hygiene.txt and raises a Windows toast when
rem any repo has stale uncommitted work or unpushed commits.
cd /d C:\Projects\foundry
C:\Python313\python.exe scripts\repo_hygiene.py --days 7
if errorlevel 1 (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null;" ^
    "$body = (Get-Content \"$env:LOCALAPPDATA\Foundry\repo_hygiene.txt\" | Where-Object { $_ -match '^  \S' } | Select-Object -First 4) -join ', ';" ^
    "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument;" ^
    "$xml.LoadXml(\"<toast scenario='reminder'><visual><binding template='ToastGeneric'><text>Repos need a commit/push</text><text>$([System.Security.SecurityElement]::Escape($body))</text><text>Details: %%LOCALAPPDATA%%\Foundry\repo_hygiene.txt</text></binding></visual></toast>\");" ^
    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Foundry').Show([Windows.UI.Notifications.ToastNotification]::new($xml))"
)
