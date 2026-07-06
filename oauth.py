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

API_URL = os.getenv("QONIC_API_URL", "https://api.qonic.com/v1").rstrip('/')
SCOPE = os.getenv("QONIC_SCOPES", "projects:read projects:write models:read models:write issues:read libraries:read libraries:write")
REDIRECT_URI = os.getenv("QONIC_REDIRECT_URI", "http://localhost:8765/callback")
LOCAL_PORT = os.getenv("QONIC_LOCAL_PORT", 8765)
CLIENT_ID = os.getenv("QONIC_CLIENT_ID")
APPLICATION_KEY = "api_python_sample"

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

def run_local_server():
    server = http.server.HTTPServer(("127.0.0.1", int(LOCAL_PORT)), OAuthHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    thread.join()
    server.server_close()
    return OAuthHandler.result

def get_client_id() -> str:
    if CLIENT_ID:
        return CLIENT_ID

    response = requests.get(f"{API_URL}/public-api-applications/config", timeout=30)
    response.raise_for_status()
    applications = response.json()
    client_id = applications.get(APPLICATION_KEY)
    if not client_id:
        raise SystemExit(
            f"No default Qonic public API application client id found for {APPLICATION_KEY}. "
            "Set QONIC_CLIENT_ID to use your own Developer Portal application."
        )

    return client_id

# --- Main login flow (now with PKCE) ----------------------------------------

def login() -> dict:
    client_id = get_client_id()

    # 1) Prepare PKCE + state
    code_verifier = make_code_verifier(64)
    code_challenge = make_code_challenge(code_verifier)
    state = make_state(24)

    # 2) Open authorize URL (with PKCE + state)
    params = {
        "client_id": client_id,
        "scope": SCOPE,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
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
    # Public client uses PKCE; no client secret is sent.
    result = requests.post(
        f"{API_URL}/auth/token",
        data={
            "client_id": client_id,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
        },
        timeout=30,
    ).json()

    if 'errorDetails' in result:
        raise SystemExit(f"Token exchange failed: {result['errorDetails']}")

    if 'access_token' not in result:
        raise SystemExit("No access token received from Qonic!")

    return result

if __name__ == "__main__":
    print(login())
