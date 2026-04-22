# IPTV Catchup Downloader

CLI tool to download IPTV replays via an Xtream Codes API.

## Requirements

- Python 3.10+
- FFmpeg: `brew install ffmpeg`

## Installation

```bash
git clone https://github.com/mrsd3/catchup-downloader.git
cd catchup-downloader
```

## Usage

```bash
python3 catchup_downloader.py
```

On first launch, the script prompts for your Xtream Codes credentials (host, port, username, password) and saves them to `~/.catchup_config.json`.

### How it works

1. Automatically fetches the live channel list
2. Search for a channel by name
3. Enter the time range (`YYYY-MM-DD HH:MM`)
4. Download with a progress bar
5. File saved to `~/Downloads/`

### File naming format

```
ChannelName_2026-04-21_2015-2030.mp4
```

## Notes

- Only channels with catchup enabled (`tv_archive: 1`) can be downloaded
- Credentials are stored locally in `~/.catchup_config.json` — do not commit this file
- Compatible with macOS (Apple Silicon and Intel)
