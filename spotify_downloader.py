"""
Spotify Music Downloader - обёртка над spotDL.

Что делает:
  1. Раз в сутки обновляет spotDL и yt-dlp (YouTube регулярно ломает старые версии).
  2. Проверяет FFmpeg и Deno и при необходимости докачивает их
     (без Deno свежий yt-dlp не может скачивать с YouTube).
  3. Качает трек / альбом / плейлист с YouTube Music и YouTube.
  4. Если с YouTube не получилось - пробует SoundCloud и Bandcamp.
  5. В конце честно показывает, что скачалось, а что нет.

Запуск:
  python spotify_downloader.py                      (спросит ссылку и папку)
  python spotify_downloader.py ССЫЛКА --folder ПАПКА

Если YouTube пишет "Sign in to confirm you're not a bot" - положи файл
cookies.txt (экспорт куки youtube.com из браузера) рядом с этим скриптом,
он подхватится автоматически.
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_FOLDER = r"C:\Users\user\Desktop\musi"
DEFAULT_FORMAT = "m4a"
OUTPUT_TEMPLATE = "{artists} - {title}.{output-ext}"

MIN_PYTHON = (3, 11)  # spotDL 4.6+ не ставится на более старый Python
SCRIPT_DIR = Path(__file__).resolve().parent
COOKIES_FILE = SCRIPT_DIR / "cookies.txt"
UPDATE_STAMP = Path(tempfile.gettempdir()) / "spotdl_last_update.txt"
ERRORS_FILE = Path(tempfile.gettempdir()) / "spotdl_errors.txt"
UPDATE_EVERY_SEC = 24 * 60 * 60
AUDIO_EXTS = {".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav"}

PRIMARY_SOURCES = ["youtube-music", "youtube"]
FALLBACK_SOURCES = ["soundcloud", "bandcamp"]


# ---------------------------------------------------------------- helpers

def run_py(args, quiet=False):
    """Запускает команду в том же Python, в котором работает скрипт."""
    extra = {}
    if quiet:
        extra = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    return subprocess.run([sys.executable, *args], **extra).returncode


def py_check(code):
    return run_py(["-c", code], quiet=True) == 0


def update_is_due():
    try:
        return time.time() - UPDATE_STAMP.stat().st_mtime > UPDATE_EVERY_SEC
    except OSError:
        return True


# ---------------------------------------------------------------- setup

def ensure_spotdl():
    installed = py_check("import spotdl")
    if installed and not update_is_due():
        return True

    if installed:
        print("Обновляю spotDL и yt-dlp (раз в сутки, ~10 сек)...")
    else:
        print("Устанавливаю spotDL (один раз, пару минут)...")

    rc = run_py([
        "-m", "pip", "install", "-U", "-q", "--disable-pip-version-check",
        "spotdl", "yt-dlp[default]",
    ])
    if rc == 0:
        try:
            UPDATE_STAMP.write_text(time.ctime(), encoding="utf-8")
        except OSError:
            pass
    elif installed:
        print("[ВНИМАНИЕ] Обновить не получилось, продолжаю с текущей версией.")

    if not py_check("import spotdl"):
        print("[ОШИБКА] spotDL не установился. Попробуй вручную:")
        print(f'  "{sys.executable}" -m pip install -U spotdl')
        return False
    return True


def ensure_tool(name, module, func, cli_flag):
    check = (
        f"from spotdl.utils.{module} import {func} as ok; "
        "raise SystemExit(0 if ok() else 1)"
    )
    if py_check(check):
        return
    print(f"Скачиваю {name} (один раз)...")
    run_py(["-m", "spotdl", cli_flag])


# ---------------------------------------------------------------- download

def parse_queries(raw):
    raw = raw.strip().strip('"').strip("'")
    if "http" not in raw:
        return [raw] if raw else []  # обычный поисковый запрос "артист - трек"
    queries = []
    for part in raw.replace('"', " ").split():
        if "open.spotify.com" in part:
            part = part.split("?", 1)[0]  # убираем ?si=...&utm_source=...
        queries.append(part)
    return queries


def audio_snapshot(folder):
    result = {}
    for f in Path(folder).rglob("*"):
        if f.suffix.lower() in AUDIO_EXTS and f.is_file():
            result[f] = f.stat().st_mtime
    return result


def spotdl_download(queries, folder, fmt, sources):
    try:
        ERRORS_FILE.unlink()
    except OSError:
        pass

    cmd = [
        "-m", "spotdl", "download", *queries,
        "--audio", *sources,
        "--format", fmt,
        "--output", str(Path(folder) / OUTPUT_TEMPLATE),
        "--save-errors", str(ERRORS_FILE),
    ]
    if COOKIES_FILE.is_file():
        cmd += ["--cookie-file", str(COOKIES_FILE)]

    rc = run_py(cmd)

    errors = []
    if ERRORS_FILE.is_file():
        text = ERRORS_FILE.read_text(encoding="utf-8", errors="replace")
        errors = [line.strip() for line in text.splitlines() if " - " in line]
    return rc, errors


def failed_urls(errors):
    urls = []
    for line in errors:
        url = line.split(" - ", 1)[0].strip()
        if url.startswith("http"):
            urls.append(url)
    return urls


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description="Spotify Music Downloader")
    parser.add_argument("url", nargs="?", help="ссылка Spotify (или несколько через пробел)")
    parser.add_argument("--folder", help="папка для сохранения")
    parser.add_argument("--format", default=DEFAULT_FORMAT, help="m4a, mp3, opus, flac...")
    parser.add_argument("--no-pause", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    print("==========================================")
    print("      SPOTIFY MUSIC DOWNLOADER")
    print("==========================================\n")

    if sys.version_info < MIN_PYTHON:
        print(f"[ОШИБКА] Нужен Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} или новее, "
              f"а запущен {sys.version.split()[0]}.")
        print("Скачай свежий Python: https://www.python.org/downloads/")
        return 1

    if not ensure_spotdl():
        return 1
    ensure_tool("FFmpeg", "ffmpeg", "is_ffmpeg_installed", "--download-ffmpeg")
    ensure_tool("Deno", "deno", "is_deno_installed", "--download-deno")

    folder = args.folder
    if not folder:
        folder = input(f"Папка для музыки [Enter = {DEFAULT_FOLDER}]: ").strip().strip('"')
        folder = folder or DEFAULT_FOLDER

    raw = args.url or input("Вставь ссылку Spotify: ")
    queries = parse_queries(raw)
    if not queries:
        print("Ошибка: ссылка не указана!")
        return 1

    os.makedirs(folder, exist_ok=True)
    before = audio_snapshot(folder)

    print("\n==========================================")
    print(f"Папка сохранения: {folder}")
    print(f"Формат: {args.format.upper()}")
    if COOKIES_FILE.is_file():
        print("Cookies: cookies.txt найден, использую")
    print("==========================================\n")

    rc, errors = spotdl_download(queries, folder, args.format, PRIMARY_SOURCES)

    if rc != 0 and not errors:
        # spotDL упал ещё до скачивания - обычно временный сбой Spotify
        print("\nSpotify не отдал данные, пробую ещё раз...\n")
        time.sleep(3)
        rc, errors = spotdl_download(queries, folder, args.format, PRIMARY_SOURCES)

    if rc != 0 and not errors:
        print("\n[ОШИБКА] Не удалось получить данные из Spotify.")
        print("Проверь ссылку и интернет и попробуй ещё раз через минуту.")
        return 1

    retry = failed_urls(errors)
    if retry:
        print(f"\nС YouTube не скачалось: {len(retry)}. Пробую SoundCloud / Bandcamp...\n")
        _, errors = spotdl_download(retry, folder, args.format, FALLBACK_SOURCES)

    after = audio_snapshot(folder)
    saved = sorted(f for f, m in after.items() if before.get(f) != m)

    print("\n==========================================")
    if saved:
        print(f"[УСПЕХ] Скачано файлов: {len(saved)}")
        for f in saved[:15]:
            print(f"  + {f.name}")
        if len(saved) > 15:
            print(f"  ... и ещё {len(saved) - 15}")
        print(f"Папка: {folder}")
    elif not errors:
        print("Новых файлов нет - похоже, эти треки уже лежат в папке.")

    if errors:
        print(f"\n[ОШИБКА] Не скачалось: {len(errors)}")
        for line in errors[:10]:
            print(f"  - {line}")
        print("\nЧто можно сделать:")
        print("  * если YouTube пишет 'Sign in to confirm you're not a bot' -")
        print(f"    положи cookies.txt с куки youtube.com сюда: {SCRIPT_DIR}")
        print("  * попробовать позже или с VPN")
    print("==========================================")
    return 1 if errors and not saved else 0


if __name__ == "__main__":
    code = main()
    if "--no-pause" not in sys.argv and sys.stdin and sys.stdin.isatty():
        input("\nНажми Enter, чтобы закрыть...")
    sys.exit(code)
