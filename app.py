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

def read_database():
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def write_database(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(DATA_FILE)

class App(BaseHTTPRequestHandler):
    def send_common(self, status, content_type, raw, cache="no-store"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.end_headers()
        self.wfile.write(raw)

    def send_json(self, payload, status=200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_common(status, "application/json; charset=utf-8", raw)

    def send_text(self, text, status=200):
        self.send_common(status, "text/plain; charset=utf-8", text.encode("utf-8"))

    def read_json_body(self):
        size = int(self.headers.get("Content-Length", "0") or "0")
        if size <= 0:
            return {}
        return json.loads(self.rfile.read(size).decode("utf-8"))

    def do_GET(self):
        path = unquote(urlparse(self.path).path)

        if path == "/health":
            return self.send_json({"status": "ok"})

        if path == "/api/status":
            db = read_database()
            return self.send_json({
                "ok": True,
                "site_status": db.get("site", {}).get("status", "Online"),
                "version": db.get("site", {}).get("version", "1.0.0"),
                "utc": datetime.now(timezone.utc).isoformat()
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

        if path in ("/", "/index.html"):
            file_path = PUBLIC / "index.html"
        else:
            file_path = (PUBLIC / path.lstrip("/")).resolve()
            try:
                file_path.relative_to(PUBLIC.resolve())
            except ValueError:
                return self.send_text("Forbidden", 403)

        if not file_path.is_file():
            return self.send_text("Not Found", 404)

        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/javascript":
            content_type += "; charset=utf-8"

        raw = file_path.read_bytes()
        cache = "public, max-age=86400" if file_path.name != "index.html" else "no-cache"
        return self.send_common(200, content_type, raw, cache)

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
    server = ThreadingHTTPServer(("0.0.0.0", port), App)
    print(f"Smell Panties web service listening on 0.0.0.0:{port}", flush=True)
    server.serve_forever()
