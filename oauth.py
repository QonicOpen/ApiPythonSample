#!/usr/bin/env python3
import http.server
import os
import threading
import urllib.parse
import webbrowser
import requests
import secrets
import string
import hashlib
import base64
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "https://api.qonic.com/v1").rstrip('/')
SCOPE = os.getenv("SCOPES", "projects:read projects:write models:read models:write issues:read libraries:read libraries:write")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8765/callback")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# --- PKCE helpers ------------------------------------------------------------

_ALPHABET = string.ascii_letters + string.digits + "-._~"  # RFC 7636 allowed chars

def make_code_verifier(length: int = 64) -> str:
    # RFC 7636: 43–128 chars from allowed set
    return ''.join(secrets.choice(_ALPHABET) for _ in range(length))

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def make_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode('ascii')).digest()
    return b64url(digest)

def make_state(length: int = 24) -> str:
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

# --- Local callback server ---------------------------------------------------

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

# --- Main login flow (now with PKCE) ----------------------------------------

def login() -> dict:
    # 1) Prepare PKCE + state
    code_verifier = make_code_verifier(64)
    code_challenge = make_code_challenge(code_verifier)
    state = make_state(24)

    # 2) Open authorize URL (with PKCE + state)
    params = {
        "clientId": CLIENT_ID,
        "scope": SCOPE,
        "redirectUri": REDIRECT_URI,
        "state": state,
        "codeChallenge": code_challenge,
        "codeChallengeMethod": "S256",
    }
    url = f"{API_URL}/auth/authorize?{urllib.parse.urlencode(params)}"
    print("Open this URL to authorize:")
    print(url)
    webbrowser.open(url)

    # 3) Wait for the local redirect
    result = run_local_server()
    if result.get("error"):
        raise SystemExit(f"Authorization failed: {result['error']}")

    # Verify state to prevent CSRF
    returned_state = result.get("state")
    if not returned_state or returned_state != state:
        raise SystemExit("Invalid state returned from Qonic (possible CSRF).")

    code = result.get("code")
    if not code:
        raise SystemExit("No code received from Qonic!")

    # 4) Exchange code for tokens (include codeVerifier)
    resp = requests.post(
        f"{API_URL}/auth/token",
        data={
            "clientId": CLIENT_ID,
            "clientSecret": CLIENT_SECRET,
            "code": code,
            "redirectUri": REDIRECT_URI,
            "codeVerifier": code_verifier,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    print(login())