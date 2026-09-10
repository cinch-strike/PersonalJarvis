"""
Read-only transcript view — the night's conversations, on your phone.
─────────────────────────────────────────────────────────────────────
Nothing here records anything. `memory.save_turn()` has been writing every turn
to SQLite since Phase 3, so this is purely a reader over data that already
exists. That matters for performance: adding this costs Vlad nothing, because
the expensive half was already happening.

⚠️ PERFORMANCE, since it is a fair thing to worry about on a party night:
  · It runs as its OWN process, not inside Vlad's loop. Nothing here can slow a
    reply down, because nothing here runs between hearing and answering.
  · SQLite is opened in WAL mode (see memory._connect), so a reader never
    blocks the writer. The page can be refreshing while Vlad is mid-sentence.
  · The page refreshes on a timer measured in seconds, not continuously, and
    renders a bounded number of turns. Someone leaving it open on a phone costs
    a few SQLite reads a minute on a 4-core Pi whose real work is waiting on
    the network.

⚠️ ACCESS: a token is REQUIRED and there is no default. Guests are on the same
WiFi, and this page is every conversation every child has had all night. Without
JARVIS_LOG_TOKEN set, the server refuses to start rather than quietly serving
it to the street. Fail closed, not open.

  python jarvis.py --log            # markdown transcript to stdout
  python jarvis.py --serve-log      # start the page (needs JARVIS_LOG_TOKEN)
"""

from __future__ import annotations

import hmac
import html
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import config
import memory

PORT = int(os.environ.get("JARVIS_LOG_PORT", "8080"))
TOKEN = os.environ.get("JARVIS_LOG_TOKEN", "").strip()
MAX_TURNS = int(os.environ.get("JARVIS_LOG_MAX_TURNS", "300"))
REFRESH_S = int(os.environ.get("JARVIS_LOG_REFRESH_S", "15"))

_SPEAKER = {"user": "Guest", "assistant": config.NAME}


def render_markdown(turns) -> str:
    """A transcript you can keep — the archive half of this feature."""
    if not turns:
        return f"# {config.NAME} — transcript\n\n_No conversations recorded yet._\n"
    out = [f"# {config.NAME} — transcript", ""]
    session = None
    for t in turns:
        if t["session_id"] != session:
            session = t["session_id"]
            out += ["", f"## Session {session}", ""]
        who = _SPEAKER.get(t["role"], t["role"])
        out.append(f"**{t['created_at']} — {who}:** {t['content']}")
        out.append("")
    return "\n".join(out) + "\n"


def group_exchanges(turns) -> list:
    """Group turns into exchanges: a guest line plus the reply it drew.

    Needed because "newest first" and "readable" pull against each other. Simply
    reversing the turns puts every answer above its own question, which is
    unreadable. Reversing EXCHANGES keeps each question above its answer while
    still putting the latest activity at the top, so nobody has to scroll a
    whole evening on a phone.
    """
    exchanges, current = [], []
    for t in turns:
        if t["role"] == "user" and current:
            exchanges.append(current)
            current = []
        current.append(t)
    if current:
        exchanges.append(current)
    return exchanges


def render_html(turns) -> str:
    """One page, readable on a phone, no external anything.

    Every piece of content is escaped: this is transcribed speech from strangers
    plus whatever the model wrote back, so it is untrusted text by definition.
    """
    rows = []
    # Newest exchange first — see group_exchanges for why not simply reversed.
    for exchange in reversed(group_exchanges(turns)):
        rows.append('<div class="exchange">')
        for t in exchange:
            who = _SPEAKER.get(t["role"], t["role"])
            cls = "guest" if t["role"] == "user" else "vlad"
            rows.append(
                f'<div class="turn {cls}"><span class="who">{html.escape(who)}</span>'
                f'<span class="time">{html.escape(t["created_at"])}</span>'
                f'<p>{html.escape(t["content"])}</p></div>'
            )
        rows.append("</div>")
    body = "\n".join(rows) or "<p class='empty'>Nothing recorded yet.</p>"
    name = html.escape(config.NAME)
    return f"""<!doctype html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{REFRESH_S}">
<title>{name} — transcript</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin:0; padding:1rem; background:#14121a; color:#e8e4f0;
         font:16px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
  h1 {{ font-size:1.3rem; margin:0 0 1rem; color:#c9a227; }}
  h2 {{ font-size:.85rem; text-transform:uppercase; letter-spacing:.08em;
        color:#7d7791; margin:2rem 0 .5rem; border-bottom:1px solid #2a2635;
        padding-bottom:.3rem; }}
  .turn {{ margin:0 0 .9rem; padding:.6rem .8rem; border-radius:.5rem;
           background:#1d1a26; border-left:3px solid #3a3450; }}
  .turn.vlad {{ border-left-color:#c9a227; }}
  .who {{ font-weight:600; margin-right:.5rem; }}
  .turn.vlad .who {{ color:#c9a227; }}
  .turn.guest .who {{ color:#8fb8de; }}
  .time {{ font-size:.72rem; color:#6c6680; }}
  p {{ margin:.35rem 0 0; }}
  .exchange {{ margin:0 0 1.4rem; padding-bottom:.4rem;
               border-bottom:1px solid #241f30; }}
  .empty {{ color:#7d7791; }}
</style></head>
<body>
<h1>{name} — transcript</h1>
<p class="time">newest first · refreshes every {REFRESH_S}s</p>
{body}
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 — BaseHTTPRequestHandler's naming
        q = parse_qs(urlparse(self.path).query)
        given = (q.get("k") or [""])[0]
        # Constant-time: a plain == leaks the token a character at a time to
        # anyone patient enough to measure.
        if not hmac.compare_digest(given, TOKEN):
            self.send_response(404)          # 404, not 403 — don't confirm it exists
            self.end_headers()
            self.wfile.write(b"Not found")
            return
        turns = memory.load_turns()[-MAX_TURNS:]
        page = render_html(turns).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(page)

    def log_message(self, *a):
        pass                                  # don't spam journalctl on every refresh


def serve() -> int:
    if not TOKEN:
        print("\n❌ JARVIS_LOG_TOKEN is not set — refusing to serve.\n")
        print("   This page is every conversation of the night and your guests")
        print("   are on the same WiFi. Set a token in jarvis.env first:\n")
        print("     JARVIS_LOG_TOKEN=$(openssl rand -hex 8)\n")
        return 1
    srv = HTTPServer(("0.0.0.0", PORT), _Handler)
    print(f"\n📖 {config.NAME} transcript on port {PORT}")
    print(f"   http://jarvis.local:{PORT}/?k={TOKEN}")
    print("   Ctrl+C to stop.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("   stopped.\n")
    return 0


def dump() -> int:
    print(render_markdown(memory.load_turns()))
    return 0
