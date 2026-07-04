@echo off
echo ========================================
echo  Starting Table Counter App
echo ========================================
echo.

echo [1/2] Installing requirements...
python -m pip install -r requirements.txt

echo.
echo [2/2] Server Start...
py app.py

pause