"""OAuth 2.1 authorization flow definition utilities."""
from __future__ import annotations

import base64
import random
import string
import webbrowser
import hashlib
import requests
from dataclasses import dataclass, fields
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from socket import socket
from typing import cast
from urllib.parse import parse_qs, urlencode, urlparse

class PKCESecret:
    """PKCE secret."""

    def __init__(self, length: int = 128):
        self.value = "".join(
            random.choices(string.ascii_letters + string.digits, k=length)
        )

    def __str__(self) -> str:
        return self.value

    def __bytes__(self) -> bytes:
        return self.value.encode()

    @property
    def challenge(self) -> bytes:
        """PKCE challenge matching the secret value."""
        return base64.urlsafe_b64encode(hashlib.sha256(bytes(self)).digest()).rstrip(
            b"="
        )

    @property
    def challenge_method(self) -> str:
        """PKCE challenge method, always 'S256' in this implementation."""
        return "S256"

class AuthorizationCodeHandler(BaseHTTPRequestHandler):
    """OAuth 2.1 authorization code flow (with PKCE) HTTP handler."""

    def __init__(
        self,
        request: socket | tuple[bytes, socket],
        client_address: tuple[str, int],
        server: RedirectionServer,
    ):
        # Required for type-checking the server object
        super().__init__(request, client_address, server)

    def log_message(self, *_: str) -> None:
        # Silence HTTP server logging to *stdout* and *stderr*
        pass

    def do_GET(self) -> None:
        # BUG: init method accepts a 'RedirectionServer'
        # but it remains a 'BaseServer' here!
        server = cast(RedirectionServer, self.server)

        url = urlparse(self.path)

        # Ignore request to a path different from the specified redirection
        if url.path != server.redirection_path:
            self.send_error(HTTPStatus.NOT_FOUND, message="Not found")
            return

        qs = parse_qs(url.query)

        # Validate state
        try:
            (query_state,) = qs.get("state", [])
            if query_state != server.state:
                server.error = RuntimeError(
                    "bad state in OAuth redirect URI: "
                    f"'{query_state}', expected '{server.state}'."
                )
        except (TypeError, ValueError):
            server.error = RuntimeError("no state in OAuth redirect URI.")

        # Get code
        try:
            (server.code,) = qs.get("code", [])
        except (TypeError, ValueError):
            server.error = RuntimeError("no code in OAuth redirect URI.")

        # Send OK or error response
        if server.error:
            self.send_error(
                HTTPStatus.BAD_REQUEST, message=f"OAuth error: {server.error}"
            )
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Connection", "close")
        self.send_header("Content-type", "text/html;utf-8")
        self.end_headers()

        self.wfile.write("""<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <title>Qonic Login</title>
            </head>
            <body>
                <h1>Authenticated!</h1>
                <p>You may now close this page.</p>
            </body>
            </html>
            """.encode(encoding="utf-8")
        )


class RedirectionServer(HTTPServer):
    """OAuth 2.1 authorization code flow (with PKCE) HTTP server."""

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[AuthorizationCodeHandler],
        redirection_path: str
    ):
        super().__init__(server_address, handler_class)

        self.redirection_path = redirection_path or "/"
        self.state = base64.urlsafe_b64encode(
            "".join(
                random.choices(string.ascii_letters + string.digits + "-._~", k=32)
            ).encode()
        ).decode()

        self.code: str | None = None
        self.error: RuntimeError | None = None


def redirection_server(redirect_uri: str) -> RedirectionServer:
    """Create a local HTTP server to handle an OAuth 2.1 authorization code redirect.

    This factory allows us to create the server from just the redirect URI.
    """
    server_conf = urlparse(redirect_uri)

    if not server_conf.hostname or not server_conf.port:
        raise ValueError("cannot start redirection server without hostname and port.")

    return RedirectionServer(
        (server_conf.hostname, server_conf.port),
        AuthorizationCodeHandler,
        redirection_path=server_conf.path
    )


def open_authorization_endpoint(
    endpoint: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    scope: str,
    pkce_secret: PKCESecret,
    audience: str
) -> None:
    """Direct the user agent to an OAuth 2.1 authorization server."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "scope": scope,
        "code_challenge": pkce_secret.challenge,
        "code_challenge_method": pkce_secret.challenge_method,
        "audience": audience,
    }
    webbrowser.open(f"{endpoint}?{urlencode(params)}")


def start_authorization_code_flow(
    endpoint: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    pkce_secret: PKCESecret,
    audience: str
) -> str:
    """Start OAuth 2.1 authorization code flow (with PKCE).

    Authorization code flow is interactive, this:
    1. opens a web browser allowing a user to log in;
    2. a local HTTP server handles the redirection from the authorization server and
       accepts the authorization code (a temporary credential used to obtain tokens).
    """
    with redirection_server(redirect_uri) as httpd:
        open_authorization_endpoint(
            endpoint=endpoint,
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=httpd.state,
            scope=scope,
            pkce_secret=pkce_secret,
            audience=audience
        )
        while not httpd.code and not httpd.error:
            httpd.handle_request()
        if httpd.error:
            raise httpd.error
        if not httpd.code:
            # This should not ever be reached.
            raise RuntimeError(  # pragma: no cover
                "no authorization code, unknown error."
            )

    return httpd.code


@dataclass(frozen=True)
class TokenResponse:
    """OAuth 2.1 token response."""

    access_token: str
    token_type: str
    expires_in: int | None = None
    created_at: int | None = None
    scope: str | None = None
    id_token: str | None = None
    refresh_token: str | None = None


def fetch_token(
    endpoint: str,
    client_id: str,
    redirect_uri: str | None = None,
    code: str | None = None,
    pkce_secret: PKCESecret | None = None,
) -> TokenResponse:
    """Fetch a token from the provider's token endpoint."""
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": str(pkce_secret),
    }


    try:
        request = requests.post(endpoint, data=data)
        request.raise_for_status()
    except requests.HTTPError as http_err:
        raise RuntimeError(f"HTTP error occurred: {http_err}")
    except Exception as err:
        raise RuntimeError(f"Other error occurred: {err}")
    else:
        token_data = request.json()
        return TokenResponse(
            **{
                key: value
                for key, value in token_data.items()
                # Ignore extra keys that are not token response fields
                if key in (field.name for field in fields(TokenResponse))
            }
        )

def login(
    issuer: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    audience: str,
) -> TokenResponse:

    pkce_secret = PKCESecret()
    code = start_authorization_code_flow(
        f"{issuer}/authorize",
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        pkce_secret=pkce_secret,
        audience=audience,
    )
    return fetch_token(
        f"{issuer}/oauth/token",
        client_id=client_id,
        redirect_uri=redirect_uri,
        code=code,
        pkce_secret=pkce_secret,
    )