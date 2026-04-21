#!/usr/bin/env python3
"""IPTV Catchup Downloader — Xtream Codes API"""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import urllib.error
import urllib.request

CONFIG_PATH = Path.home() / ".catchup_config.json"
OUTPUT_DIR = Path.home() / "Downloads"


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return prompt_and_save_config()


def prompt_and_save_config() -> dict:
    print("Premier lancement — configuration des credentials Xtream Codes")
    host = input("Host (ex: iptv.example.com) : ").strip().rstrip("/")
    port = input("Port (ex: 8080) : ").strip()
    username = input("Username : ").strip()
    password = input("Password : ").strip()

    if not host.startswith("http"):
        host = f"http://{host}"

    # Strip port if user accidentally included it in the host (e.g. http://host:8080)
    host = re.sub(r":(\d+)$", "", host)

    config = {"host": host, "port": port, "username": username, "password": password}
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Config sauvegardée dans {CONFIG_PATH}\n")
    return config


# ── API ───────────────────────────────────────────────────────────────────────

def fetch_streams(cfg: dict) -> list[dict]:
    url = (
        f"{cfg['host']}:{cfg['port']}/player_api.php"
        f"?username={cfg['username']}&password={cfg['password']}"
        f"&action=get_live_streams"
    )
    print("Récupération des chaînes live…")
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"Erreur HTTP {e.code} : {e.reason}")
    except urllib.error.URLError as e:
        sys.exit(f"Erreur : impossible de joindre {cfg['host']}:{cfg['port']} — {e.reason}")
    if not isinstance(data, list):
        sys.exit("Réponse inattendue de l'API (pas une liste de chaînes).")
    return data


# ── Channel selection ─────────────────────────────────────────────────────────

PAGE_SIZE = 20


def search_channels(streams: list[dict], query: str) -> list[dict]:
    q = query.lower()
    return [s for s in streams if q in s.get("name", "").lower()]


def display_page(results: list[dict], page: int) -> None:
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, len(results))
    print(f"\nRésultats {start + 1}–{end} sur {len(results)} :")
    for i, ch in enumerate(results[start:end], start=start + 1):
        archive = " [catchup]" if ch.get("tv_archive") == 1 else ""
        print(f"  {i:3}. {ch['name']}{archive}")


def pick_channel(streams: list[dict]) -> dict:
    while True:
        query = input("\nRecherche chaîne (nom) : ").strip()
        if not query:
            continue
        results = search_channels(streams, query)
        if not results:
            print("Aucune chaîne trouvée, réessayez.")
            continue

        page = 0
        total_pages = (len(results) - 1) // PAGE_SIZE

        while True:
            display_page(results, page)
            nav_hints = []
            if page < total_pages:
                nav_hints.append("n=suivant")
            if page > 0:
                nav_hints.append("p=précédent")
            nav_hints.append("ou entrez un numéro")
            if len(results) > PAGE_SIZE:
                nav_hints.append("q=nouvelle recherche")

            choice = input(f"Choix ({', '.join(nav_hints)}) : ").strip().lower()

            if choice == "n" and page < total_pages:
                page += 1
            elif choice == "p" and page > 0:
                page -= 1
            elif choice == "q":
                break
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(results):
                    return results[idx]
                else:
                    print(f"Numéro invalide (1–{len(results)}).")
            else:
                print("Entrée non reconnue.")


# ── Date / time input ─────────────────────────────────────────────────────────

def parse_dt(prompt: str) -> datetime:
    while True:
        raw = input(prompt).strip()
        for fmt in ("%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                pass
        print("Format attendu : YYYY-MM-DD HH:MM (ex: 2026-04-21 20:15)")


def get_timerange() -> tuple[datetime, datetime]:
    start = parse_dt("Date/heure de début (YYYY-MM-DD HH:MM) : ")
    while True:
        end = parse_dt("Date/heure de fin   (YYYY-MM-DD HH:MM) : ")
        if end > start:
            return start, end
        print("L'heure de fin doit être postérieure à l'heure de début.")


# ── Catchup URL & output path ─────────────────────────────────────────────────

def build_catchup_url(cfg: dict, channel: dict, start: datetime, end: datetime) -> str:
    duration = int((end - start).total_seconds() / 60)
    start_str = start.strftime("%Y-%m-%d:%H-%M")
    stream_id = channel["stream_id"]
    base = f"{cfg['host']}:{cfg['port']}"
    user = cfg['username']
    pwd  = cfg['password']

    # Format 1 (standard Xtream) — essayé en premier
    # Format 2 (API PHP) — activé si FORMAT=2 dans la config
    fmt = int(cfg.get("url_format", 4))

    if fmt == 2:
        # Format API PHP (player_api catchup)
        import urllib.parse
        params = urllib.parse.urlencode({
            "username": user, "password": pwd,
            "action": "catchup",
            "channel": stream_id,
            "start": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end":   end.strftime("%Y-%m-%d %H:%M:%S"),
        })
        return f"{base}/player_api.php?{params}"

    if fmt == 3:
        # Format streaming/timeshift.php
        import urllib.parse
        params = urllib.parse.urlencode({
            "username": user, "password": pwd,
            "stream": stream_id,
            "start": start_str,
            "duration": duration,
        })
        return f"{base}/streaming/timeshift.php?{params}"

    if fmt == 4:
        # Format 4 — date avec colons : YYYY-MM-DD:HH:MM
        start_str4 = start.strftime("%Y-%m-%d:%H:%M")
        return f"{base}/timeshift/{user}/{pwd}/{duration}/{start_str4}/{stream_id}.ts"

    if fmt == 5:
        # Format 5 — sans extension .ts
        return f"{base}/timeshift/{user}/{pwd}/{duration}/{start_str}/{stream_id}"

    # Format 1 — standard Xtream Codes (défaut)
    return f"{base}/timeshift/{user}/{pwd}/{duration}/{start_str}/{stream_id}.ts"


def build_output_path(channel: dict, start: datetime, end: datetime) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^\w\-]", "_", channel["name"])
    date_str = start.strftime("%Y-%m-%d")
    time_str = f"{start.strftime('%H%M')}-{end.strftime('%H%M')}"
    filename = f"{safe_name}_{date_str}_{time_str}.mp4"
    return OUTPUT_DIR / filename


# ── FFmpeg download with progress ─────────────────────────────────────────────

def check_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    # Homebrew default locations on Apple Silicon and Intel
    for candidate in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
        if os.path.isfile(candidate):
            return candidate
    sys.exit(
        "FFmpeg introuvable. Installez-le avec :\n"
        "  brew install ffmpeg"
    )


def parse_ffmpeg_time(line: str) -> int | None:
    """Return elapsed seconds from a ffmpeg progress line, or None."""
    m = re.search(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", line)
    if m:
        h, mn, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
        return int(h * 3600 + mn * 60 + s)
    return None


def render_bar(elapsed: int, total: int, width: int = 40) -> str:
    pct = min(elapsed / total, 1.0)
    filled = int(pct * width)
    bar = "#" * filled + "-" * (width - filled)
    elapsed_s = f"{elapsed // 60:02d}:{elapsed % 60:02d}"
    total_s = f"{total // 60:02d}:{total % 60:02d}"
    return f"\r[{bar}] {elapsed_s}/{total_s} ({pct:.0%})"


def download(ffmpeg: str, url: str, output: Path, total_seconds: int) -> None:
    cmd = [
        ffmpeg, "-y",
        "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        str(output),
    ]
    print(f"\nTéléchargement → {output}")
    print(f"URL : {url}\n")

    proc = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    stderr_lines = []
    try:
        for line in proc.stderr:
            stderr_lines.append(line.rstrip())
            if "Server returned" in line or "HTTP error" in line.lower():
                print(f"\nErreur HTTP FFmpeg : {line.strip()}")
            elapsed = parse_ffmpeg_time(line)
            if elapsed is not None:
                print(render_bar(elapsed, total_seconds), end="", flush=True)
    except KeyboardInterrupt:
        proc.terminate()
        print("\n\nTéléchargement annulé.")
        sys.exit(1)

    proc.wait()
    print()  # newline after progress bar

    if proc.returncode != 0:
        print("── Sortie FFmpeg ──")
        for l in stderr_lines[-30:]:
            print(l)
        sys.exit(f"\nFFmpeg a terminé avec le code {proc.returncode}.")
    print(f"Terminé : {output}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ffmpeg = check_ffmpeg()
    cfg = load_config()

    streams = fetch_streams(cfg)
    print(f"{len(streams)} chaînes récupérées.")

    channel = pick_channel(streams)
    print(f"\nChaîne sélectionnée : {channel['name']}")

    if channel.get("tv_archive") != 1:
        sys.exit(
            f"La chaîne « {channel['name']} » n'a pas le catchup activé (tv_archive != 1)."
        )

    start, end = get_timerange()
    total_seconds = int((end - start).total_seconds())

    url = build_catchup_url(cfg, channel, start, end)
    output = build_output_path(channel, start, end)

    download(ffmpeg, url, output, total_seconds)


if __name__ == "__main__":
    main()
