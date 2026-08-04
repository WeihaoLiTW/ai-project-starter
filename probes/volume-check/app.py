"""Minimal probe for verifying container storage behaviour on a PaaS.

Answers three questions that decide how the deploy skill must be ordered:

  1. Does data written BEFORE a volume is attached survive a redeploy?
  2. Does attaching a volume wipe the target directory?
  3. Does data survive a redeploy once the volume IS attached?

Stdlib only, so the image builds in seconds and there is nothing to break.

Endpoints:
  GET /              show the event log
  GET /write?msg=... append a line, then show the log
"""

import datetime
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

DATA_DIR = os.environ.get("DATA_DIR", "/data")
LOG_PATH = os.path.join(DATA_DIR, "events.log")
PORT = int(os.environ.get("PORT", "8080"))


def append(event):
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{stamp}  {event}\n")


def read_log():
    try:
        with open(LOG_PATH, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "(events.log does not exist)"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/write":
            msg = parse_qs(url.query).get("msg", ["(no message)"])[0]
            append(f"WRITE  {msg}")

        body = f"data dir : {DATA_DIR}\nlog file : {LOG_PATH}\n\n{read_log()}"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *args):
        # Silence per-request logging so the platform log only shows boots.
        pass


if __name__ == "__main__":
    append("BOOT")
    print(f"probe listening on :{PORT}, writing to {LOG_PATH}", flush=True)
    HTTPServer(("", PORT), Handler).serve_forever()
