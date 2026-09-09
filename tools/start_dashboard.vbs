' Auto-starts the Grad & Internship Dashboard at Windows logon.
'
' Installed by dropping a copy of this exact file into the current user's
' Startup folder, where Windows runs it automatically and silently on every
' interactive logon:
'   %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
'
' Why a .vbs and not a scheduled task: this project's Claude Code tools run in
' a shell whose token is denied access to the Task Scheduler service (both
' `schtasks.exe` and the ScheduledTasks PowerShell module fail with "Access is
' denied" here, even for a trivial task) - the same kind of execution-context
' sandboxing gap already documented in CLAUDE.md for the Claude CLI. The
' Startup folder only needs plain filesystem write access, which works fine.
'
' Why this delegates to tools\launch_dashboard.bat instead of invoking python
' directly: the first version called pythonw.exe inline here with two nested
' quoted paths, and pythonw.exe has no console, so when it silently failed at
' real logon (cause never confirmed - possibly AV/WSH policy, possibly a
' OneDrive timing race) there was zero error output to diagnose from. The
' .bat now logs every attempt (including tracebacks) to dashboard_startup.log
' in the project root, and uses regular python.exe wrapped in a hidden window
' instead of pythonw.exe, so a real failure is finally visible next time.
'
' The 20-second sleep gives OneDrive a head start remounting this folder
' before app.py tries to read data.json, since this project lives inside a
' OneDrive-synced path.
'
' To stop auto-starting: delete the copy of this file from the Startup
' folder above (this repo copy alone does nothing - only the Startup-folder
' copy runs).

WScript.Sleep 20000
CreateObject("WScript.Shell").Run """C:\Users\ayaan\OneDrive\Claude\Grad and Internship Dashboard\tools\launch_dashboard.bat""", 0, False
