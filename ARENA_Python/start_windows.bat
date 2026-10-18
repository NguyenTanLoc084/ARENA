@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3.11 --version >nul 2>&1
if errorlevel 1 (
 echo Can cai Python 3.11 va Python Launcher truoc khi chay.
 pause
 exit /b 1
)
if not exist .venv\Scripts\python.exe py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
 echo Cai thu vien khong thanh cong. Kiem tra ket noi mang.
 pause
 exit /b 1
)
echo Mo trinh duyet tai http://127.0.0.1:5000
.venv\Scripts\python.exe run.py --demo
pause
