# Smell Panties — Render Web Service

Upload the CONTENTS of this ZIP directly to the root of your GitHub repository.

## Render settings

Create a **Web Service** and connect the GitHub repository.

- Runtime: Python 3
- Root Directory: leave blank
- Build Command: `echo "No build required"`
- Start Command: `python app.py`
- Health Check Path: `/health`

## Architecture

- HTML/CSS/JS UI: `public/`
- Python backend: `app.py`
- JSON database: `data/database.json`
- TXT temp/orchestration: `temp/tasks.txt` and `temp/runtime.txt`
- Render config: `render.yaml`

## Routes

- `/` website
- `/health` health check
- `/api/status` backend status
- `/api/data` JSON data
- `/api/tasks` TXT orchestration queue

Render's normal filesystem is ephemeral. The JSON/TXT files are appropriate for initial state and temporary orchestration. Use a persistent disk or external DB later for permanent production writes.
