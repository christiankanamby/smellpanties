#!/usr/bin/env python3
import json
import mimetypes
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
DATA_FILE = ROOT / "data" / "database.json"
TASK_FILE = ROOT / "temp" / "tasks.txt"

FALLBACK_HTML = b"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smell Panties - Coming Soon</title>
<style>
html,body{margin:0;min-height:100%;background:#080303;color:#fff;font-family:Arial,sans-serif}
body{display:grid;place-items:center;text-align:center}
main{padding:40px}
h1{font-family:Georgia,serif;font-size:clamp(44px,8vw,84px);font-weight:400;color:#efaa91;margin:20px 0}
p{color:#d4b3a8;line-height:1.7}
</style>
</head>
<body><main><h1>Under Construction</h1>
<p>Our website is currently under construction. Please come back soon.</p>
<p>Notre site est actuellement en construction. Revenez bientot.</p>
</main></body></html>"""

def read_database():
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def write_database(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

def find_file(relative_name):
    relative_name = relative_name.lstrip("/")
    candidates = [
        PUBLIC / relative_name,
        ROOT / relative_name,
    ]
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            allowed = (
                resolved == ROOT.resolve()
                or ROOT.resolve() in resolved.parents
            )
            if allowed and resolved.is_file():
                return resolved
        except Exception:
            pass
    return None

def find_index():
    for candidate in [PUBLIC / "index.html", ROOT / "index.html"]:
        if candidate.is_file():
            return candidate
    return None

class App(BaseHTTPRequestHandler):
    server_version = "SmellPantiesRender/2.0"

    def send_bytes(self, raw, content_type, status=200, cache="no-store"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.end_headers()
        self.wfile.write(raw)

    def send_json(self, payload, status=200):
        self.send_bytes(
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
            status
        )

    def serve_file(self, file_path):
        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {
            "application/javascript",
            "application/json",
        }:
            content_type += "; charset=utf-8"
        cache = "no-cache" if file_path.name == "index.html" else "public, max-age=86400"
        self.send_bytes(file_path.read_bytes(), content_type, 200, cache)

    def serve_index(self):
        index = find_index()
        if index:
            return self.serve_file(index)
        return self.send_bytes(FALLBACK_HTML, "text/html; charset=utf-8")

    def read_json_body(self):
        size = int(self.headers.get("Content-Length", "0") or "0")
        if size <= 0:
            return {}
        return json.loads(self.rfile.read(size).decode("utf-8"))

    def do_GET(self):
        path = unquote(urlparse(self.path).path)

        if path == "/health":
            return self.send_json({
                "status": "ok",
                "root": str(ROOT),
                "index_found": bool(find_index()),
            })

        if path == "/api/status":
            db = read_database()
            return self.send_json({
                "ok": True,
                "site_status": db.get("site", {}).get("status", "Under construction"),
                "version": db.get("site", {}).get("version", "2.0.0"),
                "utc": datetime.now(timezone.utc).isoformat(),
                "index_found": bool(find_index()),
            })

        if path == "/api/data":
            return self.send_json(read_database())

        if path == "/api/tasks":
            TASK_FILE.parent.mkdir(parents=True, exist_ok=True)
            TASK_FILE.touch(exist_ok=True)
            tasks = [
                line.strip()
                for line in TASK_FILE.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
            return self.send_json({"tasks": tasks})

        # Homepage always serves the index.
        if path in ("", "/", "/index.html"):
            return self.serve_index()

        # Serve static assets from /public first, then repo root.
        file_path = find_file(path)
        if file_path:
            return self.serve_file(file_path)

        # Important: never show a plain "Not Found" page for browser routes.
        # Unknown GET routes fall back to the landing page.
        return self.serve_index()

    def do_POST(self):
        path = unquote(urlparse(self.path).path)

        if path == "/api/data":
            try:
                incoming = self.read_json_body()
                if not isinstance(incoming, dict):
                    return self.send_json({"ok": False, "error": "JSON object required"}, 400)
                db = read_database()
                db.update(incoming)
                write_database(db)
                return self.send_json({"ok": True, "data": db})
            except Exception as exc:
                return self.send_json({"ok": False, "error": str(exc)}, 400)

        if path == "/api/tasks":
            try:
                incoming = self.read_json_body()
                task = str(incoming.get("task", "")).strip()
                if not task:
                    return self.send_json({"ok": False, "error": "task is required"}, 400)
                TASK_FILE.parent.mkdir(parents=True, exist_ok=True)
                with TASK_FILE.open("a", encoding="utf-8") as f:
                    f.write(task.replace("\n", " ") + "\n")
                return self.send_json({"ok": True, "task": task}, 201)
            except Exception as exc:
                return self.send_json({"ok": False, "error": str(exc)}, 400)

        return self.send_json({"ok": False, "error": "Not Found"}, 404)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    print(f"Starting Smell Panties on port {port}", flush=True)
    print(f"ROOT={ROOT}", flush=True)
    print(f"INDEX={find_index()}", flush=True)
    server = ThreadingHTTPServer(("0.0.0.0", port), App)
    server.serve_forever()
