# Spotify Downloader

Обёртка над [spotDL](https://github.com/spotDL/spotify-downloader) для Windows: вставляешь ссылку Spotify (трек, альбом или плейлист) и получаешь `.m4a` с тегами и обложкой.

## Запуск

Двойной клик по `Spotify_Downloader.bat`, затем вставить ссылку.

Нужен Python 3.11 или новее ([python.org](https://www.python.org/downloads/), при установке отметить «Add python.exe to PATH»). Всё остальное скрипт ставит сам.

Можно запускать и напрямую:

```
python spotify_downloader.py "https://open.spotify.com/track/..." --folder "D:\Music" --format mp3
```

## Что делает скрипт

- раз в сутки обновляет spotDL и yt-dlp: YouTube регулярно ломает старые версии;
- сам докачивает FFmpeg и Deno, без Deno yt-dlp не скачивает с YouTube;
- отрезает от ссылки `?si=...&utm_source=...`;
- качает с YouTube Music и YouTube, а если не вышло, пробует SoundCloud и Bandcamp;
- в конце показывает, какие файлы реально сохранились и что не скачалось
  (сам spotDL возвращает код 0 даже при ошибке).

## Настройки

- Папка по умолчанию задаётся в `Spotify_Downloader.bat` (`FOLDER`) и в `spotify_downloader.py` (`DEFAULT_FOLDER`).
- Если YouTube пишет «Sign in to confirm you're not a bot», положи рядом со скриптом `cookies.txt` с куки youtube.com, экспортированными из браузера. Файл подхватится автоматически. В репозиторий он не попадёт, так как указан в `.gitignore`.
