# Catchup Downloader

Outil CLI pour télécharger des replays IPTV via une API Xtream Codes.

## Prérequis

- Python 3.10+
- FFmpeg : `brew install ffmpeg`

## Installation

```bash
git clone https://github.com/VOTRE_USERNAME/catchup-downloader.git
cd catchup-downloader
```

## Utilisation

```bash
python3 catchup_downloader.py
```

Au premier lancement, le script demande les credentials Xtream Codes (host, port, username, password) et les sauvegarde dans `~/.catchup_config.json`.

### Déroulement

1. Récupération automatique de la liste des chaînes live
2. Recherche d'une chaîne par nom
3. Saisie de la plage horaire (`YYYY-MM-DD HH:MM`)
4. Téléchargement avec barre de progression
5. Fichier sauvegardé dans `~/Downloads/`

### Format de nommage des fichiers

```
NomChaine_2026-04-21_2015-2030.mp4
```

## Notes

- Seules les chaînes avec le catchup activé (`tv_archive: 1`) sont téléchargeables
- Les credentials sont stockés localement dans `~/.catchup_config.json` — ne pas versionner ce fichier
- Compatible macOS (Apple Silicon et Intel)
