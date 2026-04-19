"""
Local web UI for testing the movie bot in a browser.

Usage:
    python -m tests.test_web

Then open http://localhost:8080 in your browser.
"""

import sys
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

import movie_client

HTML = """<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="utf-8">
<title>קינומן - Movie Bot</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0b141a; color: #e9edef; height: 100vh; display: flex;
         flex-direction: column; }
  .header { background: #202c33; padding: 12px 20px; font-size: 18px;
            font-weight: 600; border-bottom: 1px solid #2a3942; }
  .chat { flex: 1; overflow-y: auto; padding: 20px; display: flex;
          flex-direction: column; gap: 8px; }
  .msg { max-width: 80%; padding: 8px 12px; border-radius: 8px;
         white-space: pre-wrap; line-height: 1.5; font-size: 14px; }
  .msg.user { background: #005c4b; align-self: flex-start; border-top-right-radius: 0; }
  .msg.bot { background: #202c33; align-self: flex-end; border-top-left-radius: 0; }
  .msg.bot .buttons { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
  .msg.bot .buttons button { background: none; border: 1px solid #00a884;
    color: #00a884; padding: 4px 12px; border-radius: 16px; cursor: pointer;
    font-size: 13px; }
  .msg.bot .buttons button:hover { background: #00a884; color: #111b21; }
  .input-area { background: #202c33; padding: 10px 20px; display: flex; gap: 10px;
                border-top: 1px solid #2a3942; }
  .input-area input { flex: 1; background: #2a3942; border: none; color: #e9edef;
    padding: 10px 14px; border-radius: 8px; font-size: 15px; outline: none; }
  .input-area button { background: #00a884; border: none; color: #111b21;
    padding: 10px 20px; border-radius: 8px; font-size: 15px; cursor: pointer;
    font-weight: 600; }
  .spinner { display: inline-block; width: 20px; height: 20px;
    border: 2px solid #2a3942; border-top-color: #00a884;
    border-radius: 50%; animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="header">🎬 קינומן — Movie Bot</div>
<div class="chat" id="chat"></div>
<div class="input-area">
  <input id="input" placeholder="...הקלד שם סרט" autofocus
         onkeydown="if(event.key==='Enter')send()">
  <button onclick="send()">שלח</button>
</div>
<script>
const chat = document.getElementById('chat');
const input = document.getElementById('input');

function addMsg(text, cls, buttons) {
  const d = document.createElement('div');
  d.className = 'msg ' + cls;
  d.textContent = text;
  if (buttons && buttons.length) {
    const bc = document.createElement('div');
    bc.className = 'buttons';
    buttons.forEach(b => {
      const btn = document.createElement('button');
      btn.textContent = b.title;
      btn.onclick = () => pick(b.id);
      bc.appendChild(btn);
    });
    d.appendChild(bc);
  }
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
  return d;
}

function showSpinner() {
  const d = document.createElement('div');
  d.className = 'msg bot';
  d.id = 'spinner';
  d.innerHTML = '<div class="spinner"></div>';
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}
function hideSpinner() {
  const s = document.getElementById('spinner');
  if (s) s.remove();
}

async function send() {
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  addMsg(text, 'user');
  showSpinner();
  const resp = await fetch('/api/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query: text})
  });
  hideSpinner();
  const data = await resp.json();
  if (data.type === 'details') {
    addMsg(data.text, 'bot');
  } else if (data.type === 'options') {
    addMsg('מצאתי כמה אפשרויות — למה התכוונת?', 'bot', data.options);
  } else {
    addMsg(data.text, 'bot');
  }
}

async function pick(id) {
  showSpinner();
  const resp = await fetch('/api/details', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id: parseInt(id)})
  });
  hideSpinner();
  const data = await resp.json();
  addMsg(data.text, 'bot');
}
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        if self.path == "/api/search":
            query = body["query"]
            results = movie_client.search_movie(query)
            # If no direct match and looks like a description, use LLM
            if not results and movie_client.is_description(query):
                guesses = movie_client.guess_movie_from_description(query)
                for guess in guesses:
                    results = movie_client.search_movie(guess)
                    if results:
                        break
            if not results:
                resp = {"type": "error", "text": "לא מצאתי סרט מתאים. נסה לתאר אחרת או לחפש בשם 🙏"}
            elif len(results) == 1:
                details = movie_client.get_movie_details(results[0]["id"])
                if details:
                    resp = {"type": "details", "text": movie_client.format_movie_response(details)}
                else:
                    resp = {"type": "error", "text": "לא הצלחתי לטעון פרטים. נסה שוב 🙏"}
            else:
                options = []
                for r in results[:3]:
                    title = r["title"]
                    if r["original_title"] and r["original_title"] != r["title"]:
                        title = f"{r['title']} / {r['original_title']}"
                    year = f" ({r['year']})" if r["year"] else ""
                    options.append({"id": str(r["id"]), "title": f"{title}{year}"})
                resp = {"type": "options", "options": options}

        elif self.path == "/api/details":
            tmdb_id = body["id"]
            details = movie_client.get_movie_details(tmdb_id)
            if details:
                resp = {"type": "details", "text": movie_client.format_movie_response(details)}
            else:
                resp = {"type": "error", "text": "לא הצלחתי לטעון פרטים. נסה שוב 🙏"}
        else:
            resp = {"type": "error", "text": "Unknown endpoint"}

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(resp, ensure_ascii=False).encode())

    def log_message(self, fmt, *args):
        pass  # suppress request logs


if __name__ == "__main__":
    port = 8888
    server = HTTPServer(("", port), Handler)
    print(f"🎬 קינומן running at http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nלהתראות! 👋")
