#!/usr/bin/env python3
import http.server
import os
import threading
import urllib.parse
import webbrowser
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "https://api.qonic.com/v1").rstrip('/')
SCOPE = os.getenv("SCOPES", "projects:read projects:write models:read models:write issues:read libraries:read libraries:write")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8765/callback")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

class OAuthHandler(http.server.BaseHTTPRequestHandler):
    result = {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        qs = urllib.parse.parse_qs(parsed.query)
        OAuthHandler.result["code"] = qs.get("code", [None])[0]
        OAuthHandler.result["state"] = qs.get("state", [None])[0]
        OAuthHandler.result["error"] = qs.get("error", [None])[0]

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h3>Qonic OAuth completed. You can close this tab.</h3>")

    def log_message(self, fmt, *args):
        return


def run_local_server(port=8765):
    server = http.server.HTTPServer(("127.0.0.1", port), OAuthHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    thread.join()
    server.server_close()
    return OAuthHandler.result

def login() -> dict:
    params = {
        "clientId": CLIENT_ID,
        "scope": SCOPE,
        "redirectUri": REDIRECT_URI,
    }
    url = f"{API_URL}/auth/authorize?{urllib.parse.urlencode(params)}"
    print("Open this URL in your browser to authorize:")
    print(url)
    webbrowser.open(url)

    result = run_local_server()
    code = result.get("code")
    if not code:
        raise SystemExit("No code received from Qonic!")

    resp = requests.post(f"{API_URL}/auth/token", data={
        "clientId": CLIENT_ID,
        "clientSecret": CLIENT_SECRET,
        "code": code,
        "redirectUri": REDIRECT_URI
    })
    resp.raise_for_status()
    return resp.json()