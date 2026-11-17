"""Read-only local dashboard for the lightweight SIEM (standard library only)."""
from __future__ import annotations

import argparse
import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .config import load_config
from .siem import SQLiteSiemStore


def _limit(query: str, default: int = 50) -> int:
    try:
        value = int(parse_qs(query).get("limit", [str(default)])[0])
    except (TypeError, ValueError):
        return default
    return max(1, min(value, 200))


def render_dashboard_html(store: SQLiteSiemStore, *, limit: int = 50) -> str:
    """Render escaped, read-only incident and event tables."""
    incidents = store.list_incidents()[:limit]
    events = store.list_events(limit=limit)
    incident_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item['status']))}</td>"
        f"<td>{html.escape(str(item['severity']))}</td>"
        f"<td>{html.escape(str(item['host']))}</td>"
        f"<td>{float(item['confidence']):.3f}</td>"
        f"<td>{html.escape(str(item['summary']))}</td>"
        f"<td>{html.escape(str(item['last_seen']))}</td>"
        "</tr>"
        for item in incidents
    ) or '<tr><td colspan="6">Aucun incident enregistré</td></tr>'
    event_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('timestamp', '')))}</td>"
        f"<td>{html.escape(str(item.get('src_ip') or ''))}</td>"
        f"<td>{html.escape(str(item.get('dst_ip') or ''))}</td>"
        f"<td>{html.escape(str(item.get('event_type') or ''))}</td>"
        f"<td>{html.escape(str(item.get('source_component') or ''))}</td>"
        "</tr>"
        for item in events
    ) or '<tr><td colspan="5">Aucun événement enregistré</td></tr>'
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="15">
<title>GNN-SDN-APT — SIEM léger</title>
<style>
body{{font:15px system-ui,sans-serif;max-width:1200px;margin:2rem auto;padding:0 1rem;background:#f6f7f9;color:#17202a}}
h1,h2{{color:#17202a}}.note{{color:#52606d}}section{{background:white;padding:1rem;margin:1rem 0;border-radius:10px;overflow:auto}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:.6rem;border-bottom:1px solid #e5e7eb}}
th{{background:#f0f2f5}}code{{background:#eef;padding:.15rem .3rem;border-radius:4px}}
</style></head><body>
<h1>SIEM léger — supervision SDN</h1>
<p class="note">Vue locale en lecture seule · actualisation toutes les 15 secondes · aucun contrôle de mitigation depuis cette interface.</p>
<section><h2>Incidents ({len(incidents)})</h2>
<table><thead><tr><th>Statut</th><th>Gravité</th><th>Hôte</th><th>Confiance</th><th>Résumé</th><th>Dernière observation</th></tr></thead>
<tbody>{incident_rows}</tbody></table></section>
<section><h2>Événements récents ({len(events)})</h2>
<table><thead><tr><th>Horodatage</th><th>Source</th><th>Destination</th><th>Type</th><th>Composant</th></tr></thead>
<tbody>{event_rows}</tbody></table></section>
<p class="note">API en lecture seule : <code>/api/incidents</code> · <code>/api/events</code></p>
</body></html>"""


def create_handler(database_path: str):
    class DashboardHandler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            store = SQLiteSiemStore(database_path)
            limit = _limit(parsed.query)
            if parsed.path == "/":
                body = render_dashboard_html(store, limit=limit).encode("utf-8")
                self._send(200, body, "text/html; charset=utf-8")
            elif parsed.path == "/api/incidents":
                body = json.dumps(store.list_incidents()[:limit], ensure_ascii=False).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
            elif parsed.path == "/api/events":
                body = json.dumps(store.list_events(limit=limit), ensure_ascii=False).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
            else:
                self._send(404, b'{"error":"not_found"}', "application/json; charset=utf-8")

        def do_POST(self):
            self._send(405, b'{"error":"read_only"}', "application/json; charset=utf-8")

        def log_message(self, format, *args):
            # Keep routine polling quiet; the server remains local by default.
            return

    return DashboardHandler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    config = load_config(args.config)
    database_path = config["paths"].get("siem_db", "data/siem/siem.db")
    server = ThreadingHTTPServer((args.host, args.port), create_handler(database_path))
    print(f"SIEM dashboard (read-only): http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
