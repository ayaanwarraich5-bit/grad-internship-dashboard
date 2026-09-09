@echo off
echo ---- launch attempt %date% %time% ---- >> "C:\Users\ayaan\OneDrive\Claude\Grad and Internship Dashboard\dashboard_startup.log"
"C:\Users\ayaan\AppData\Local\Programs\Python\Python312\python.exe" "C:\Users\ayaan\OneDrive\Claude\Grad and Internship Dashboard\app.py" >> "C:\Users\ayaan\OneDrive\Claude\Grad and Internship Dashboard\dashboard_startup.log" 2>&1
