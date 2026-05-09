@echo off
echo ==========================================
echo   Agente Organizador de Descargas
echo ==========================================
cd /d "%~dp0"
python organizer.py %*
echo.
echo Presiona cualquier tecla para salir...
pause > nul
