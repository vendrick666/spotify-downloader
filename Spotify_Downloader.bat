@echo off
chcp 65001 >nul
title Spotify Music Downloader
color 0B

:: Папка, куда сохранять музыку
set "FOLDER=C:\Users\user\Desktop\musi"

:: Ищем Python: сначала py-лаунчер (он берёт самую новую версию), потом python
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY goto :nopython

:: Вся логика (обновление, FFmpeg, Deno, скачивание, запасной источник) - в .py
%PY% "%~dp0spotify_downloader.py" --folder "%FOLDER%" --no-pause

echo.
pause
exit /b

:nopython
echo [ОШИБКА] Python не найден.
echo Установи Python 3.11 или новее: https://www.python.org/downloads/
echo При установке отметь галочку "Add python.exe to PATH".
echo.
pause
exit /b 1
