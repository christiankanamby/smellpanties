# Fix for Render showing `Not Found`

This commit makes `/` always serve the landing page.

It also:
- keeps `public/index.html`
- adds a root-level `index.html` fallback
- serves assets from both `public/` and the repo root
- falls back to the landing page for unknown GET routes
- exposes `/health` with `index_found` for debugging

Render settings:

Build Command:
`echo "No build required"`

Start Command:
`python app.py`

Root Directory:
leave blank

Health Check:
`/health`
