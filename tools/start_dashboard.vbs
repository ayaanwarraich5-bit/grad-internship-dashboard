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
' The 20-second sleep gives OneDrive a head start remounting this folder
' before app.py tries to read data.json, since this project lives inside a
' OneDrive-synced path.
'
' pythonw.exe (not python.exe) is used deliberately so no console window
' ever appears at logon.
'
' To stop auto-starting: delete the copy of this file from the Startup
' folder above (this repo copy alone does nothing - only the Startup-folder
' copy runs).

WScript.Sleep 20000
CreateObject("WScript.Shell").Run """C:\Users\ayaan\AppData\Local\Programs\Python\Python312\pythonw.exe"" ""C:\Users\ayaan\OneDrive\Claude\Grad and Internship Dashboard\app.py""", 0, False
