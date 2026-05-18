#!/usr/bin/env python3
"""Tiny HTTP server for the lakehouse demo dashboard.

- Serves files from ./demo/
- Proxies /api/status?url=... to bypass browser CORS so the dashboard can
  ping every service from one origin.
- Proxies /api/metric?source=... for live row/object/message counts.

Run: ./scripts/demo_serve.py  (then open http://localhost:7777)
"""
from __future__ import annotations

import json
import shlex
import socket
import subprocess
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = ROOT / "demo"
PORT = 7777


def docker_exec(container: str, cmd: str, timeout: int = 6) -> tuple[int, str]:
    """Run a command in a docker container, return (rc, stdout-stripped)."""
    full = ["docker", "exec", container, "sh", "-lc", cmd]
    try:
        out = subprocess.run(
            full, capture_output=True, text=True, timeout=timeout
        )
        return out.returncode, (out.stdout or "").strip()
    except Exception as e:
        return 1, f"err:{e}"


def http_probe(url: str, timeout: float = 3.0) -> dict:
    """Probe URL via curl, return {code, ms}."""
    cmd = [
        "curl", "-s", "-o", "/dev/null",
        "-w", "%{http_code} %{time_total}",
        "--max-time", str(timeout), url,
    ]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1)
        parts = (r.stdout or "0 0").split()
        code = int(parts[0]) if parts and parts[0].isdigit() else 0
        ms = int(float(parts[1]) * 1000) if len(parts) > 1 else int((time.time() - t0) * 1000)
        return {"code": code, "ms": ms}
    except Exception:
        return {"code": 0, "ms": int((time.time() - t0) * 1000)}


METRICS = {
    # postgres
    "pg_orders": ("de_postgres",
                  "psql -U de_user -d de_db -tA -c 'SELECT COUNT(*) FROM orders'"),
    "pg_fact_orders": ("de_postgres",
                       "psql -U de_user -d de_db -tA -c 'SELECT COUNT(*) FROM bootcamp_dw.fact_orders'"),
    "pg_lab06_orders": ("de_postgres",
                        "psql -U de_user -d de_db -tA -c 'SELECT COUNT(*) FROM lab06_dw.fact_orders'"),

    # trino lakehouse
    "trino_bronze": ("trino",
                     "trino --execute 'SELECT COUNT(*) FROM lakehouse.bronze.orders_raw'"),
    "trino_silver": ("trino",
                     "trino --execute 'SELECT COUNT(*) FROM lakehouse.silver.orders_clean'"),
    "trino_gold": ("trino",
                   "trino --execute 'SELECT COUNT(*) FROM lakehouse.gold.customer_sales'"),

    # minio image lacks awk/sed/grep — use cut on the tab-separated `mc du` output.
    "minio_objects": ("minio",
                      "mc alias set local http://localhost:9000 minio minio12345 >/dev/null 2>&1; "
                      "mc du local/lakehouse 2>/dev/null | head -1 | cut -f2 | cut -d' ' -f1"),
    "minio_bytes": ("minio",
                    "mc alias set local http://localhost:9000 minio minio12345 >/dev/null 2>&1; "
                    "mc du local/lakehouse 2>/dev/null | head -1 | cut -f1"),

    # kafka
    "kafka_orders": ("kafka",
                     "kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 "
                     "--topic orders 2>/dev/null | awk -F: '{s+=$3} END{print s+0}'"),
    "kafka_topics": ("kafka",
                     "kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null | wc -l"),

    # airflow — read directly from the metadata DB; CLI needs `docker exec -u airflow`
    # which `docker_exec()` below doesn't support.
    "airflow_dags": ("de_airflow_db",
                     "psql -U airflow -d airflow -tA -c 'SELECT COUNT(*) FROM dag'"),
    "airflow_runs": ("de_airflow_db",
                     "psql -U airflow -d airflow -tA -c "
                     "\"SELECT COUNT(*) FROM dag_run WHERE dag_id='lab13_end_to_end_pipeline'\""),
}


def get_metric(name: str) -> str:
    spec = METRICS.get(name)
    if not spec:
        return "?"
    container, cmd = spec
    rc, out = docker_exec(container, cmd)
    if rc != 0 or not out:
        return "—"
    # Strip surrounding quotes from trino output, strip "rows" etc.
    out = out.replace('"', '').strip()
    return out.splitlines()[-1].strip() if out else "—"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[demo] " + (fmt % args) + "\n")

    def _send_json(self, payload, code=200):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, fpath: Path):
        if not fpath.is_file():
            self.send_error(404)
            return
        ext = fpath.suffix.lower()
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css",
            ".js": "application/javascript",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".json": "application/json",
        }.get(ext, "application/octet-stream")
        data = fpath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)

        if u.path == "/api/status":
            url = q.get("url", [""])[0]
            if not url:
                return self._send_json({"error": "missing url"}, 400)
            return self._send_json(http_probe(url))

        if u.path == "/api/metric":
            src = q.get("source", [""])[0]
            return self._send_json({"value": get_metric(src)})

        if u.path == "/api/bulk":
            # one-shot collection for the whole dashboard
            services = json.loads(q.get("services", ["[]"])[0])
            metrics = json.loads(q.get("metrics", ["[]"])[0])
            return self._send_json({
                "services": {s["id"]: http_probe(s["url"]) for s in services},
                "metrics":  {m: get_metric(m) for m in metrics},
                "ts": int(time.time()),
            })

        if u.path in ("/", ""):
            return self._send_file(DEMO_DIR / "dashboard.html")

        # Static file (sanitize path)
        rel = u.path.lstrip("/")
        safe = (DEMO_DIR / rel).resolve()
        if DEMO_DIR.resolve() not in safe.parents and safe != DEMO_DIR.resolve():
            return self.send_error(403)
        return self._send_file(safe)


def main() -> None:
    if not DEMO_DIR.is_dir():
        print(f"[!] {DEMO_DIR} not found", file=sys.stderr)
        sys.exit(1)
    addr = ("127.0.0.1", PORT)
    try:
        srv = ThreadingHTTPServer(addr, Handler)
    except OSError as e:
        print(f"[!] bind {addr} failed: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"[demo] dashboard:  http://{addr[0]}:{addr[1]}")
    print(f"[demo] serving:    {DEMO_DIR}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[demo] bye.")


if __name__ == "__main__":
    main()
