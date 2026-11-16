import hashlib
import json
import secrets
import string
import webbrowser

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from app.config.settings import settings


TOKEN_FILE = Path("secrets/tiktok_token.json")

SCOPES = [
    "user.info.basic",
    "video.publish",
]


def _generate_code_verifier(length: int = 64) -> str:
    chars = (
        string.ascii_letters
        + string.digits
        + "-._~"
    )

    return "".join(
        secrets.choice(chars)
        for _ in range(length)
    )


def _generate_code_challenge(
    code_verifier: str,
) -> str:
    # В Desktop OAuth TikTok использует
    # SHA256 в HEX-представлении.
    return hashlib.sha256(
        code_verifier.encode("utf-8")
    ).hexdigest()


def _exchange_code_for_token(
    code: str,
    code_verifier: str,
) -> dict:

    response = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        headers={
            "Content-Type":
                "application/x-www-form-urlencoded",
        },
        data={
            "client_key":
                settings.TIKTOK_CLIENT_KEY,

            "client_secret":
                settings.TIKTOK_CLIENT_SECRET,

            "code":
                code,

            "grant_type":
                "authorization_code",

            "redirect_uri":
                settings.TIKTOK_REDIRECT_URI,

            "code_verifier":
                code_verifier,
        },
        timeout=30,
    )

    try:
        data = response.json()

    except ValueError:
        raise RuntimeError(
            "TikTok returned invalid JSON: "
            f"{response.text}"
        )

    if not response.ok or "error" in data:
        raise RuntimeError(
            f"TikTok token error: {data}"
        )

    return data


def authorize_tiktok() -> dict:

    if not settings.TIKTOK_CLIENT_KEY:
        raise ValueError(
            "TIKTOK_CLIENT_KEY is not configured"
        )

    if not settings.TIKTOK_CLIENT_SECRET:
        raise ValueError(
            "TIKTOK_CLIENT_SECRET is not configured"
        )

    state = secrets.token_urlsafe(32)

    code_verifier = (
        _generate_code_verifier()
    )

    code_challenge = (
        _generate_code_challenge(
            code_verifier
        )
    )

    params = {
        "client_key":
            settings.TIKTOK_CLIENT_KEY,

        "scope":
            ",".join(SCOPES),

        "response_type":
            "code",

        "redirect_uri":
            settings.TIKTOK_REDIRECT_URI,

        "state":
            state,

        "code_challenge":
            code_challenge,

        "code_challenge_method":
            "S256",
    }

    auth_url = (
        "https://www.tiktok.com/v2/auth/authorize/?"
        + urlencode(params)
    )

    result = {}

    class CallbackHandler(
        BaseHTTPRequestHandler
    ):

        def do_GET(self):
            parsed = urlparse(self.path)

            if (
                parsed.path
                != "/tiktok/callback/"
            ):
                self.send_response(404)
                self.end_headers()
                return

            query = parse_qs(
                parsed.query
            )

            if "error" in query:
                result["error"] = {
                    "error":
                        query.get(
                            "error",
                            [None],
                        )[0],

                    "description":
                        query.get(
                            "error_description",
                            [None],
                        )[0],
                }

                self._send_page(
                    "TikTok authorization failed."
                )

                return

            returned_state = query.get(
                "state",
                [None],
            )[0]

            if returned_state != state:
                result["error"] = (
                    "OAuth state mismatch"
                )

                self._send_page(
                    "OAuth state validation failed."
                )

                return

            code = query.get(
                "code",
                [None],
            )[0]

            if not code:
                result["error"] = (
                    "Authorization code not found"
                )

                self._send_page(
                    "Authorization code not found."
                )

                return

            try:
                print(
                    "TikTok: authorization "
                    "code received"
                )

                token_data = (
                    _exchange_code_for_token(
                        code,
                        code_verifier,
                    )
                )

                TOKEN_FILE.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                TOKEN_FILE.write_text(
                    json.dumps(
                        token_data,
                        indent=2,
                    ),
                    encoding="utf-8",
                )

                result[
                    "token_data"
                ] = token_data

                self._send_page(
                    "TikTok authorization "
                    "successful. "
                    "You can close this tab."
                )

            except Exception as error:
                result["error"] = str(
                    error
                )

                self._send_page(
                    "TikTok authorization "
                    "failed. Check terminal."
                )

        def _send_page(
            self,
            message: str,
        ):
            body = (
                "<html>"
                "<body>"
                f"<h2>{message}</h2>"
                "</body>"
                "</html>"
            ).encode("utf-8")

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8",
            )

            self.send_header(
                "Content-Length",
                str(len(body)),
            )

            self.end_headers()

            self.wfile.write(
                body
            )

        def log_message(
            self,
            format,
            *args,
        ):
            pass

    server = HTTPServer(
        ("127.0.0.1", 8001),
        CallbackHandler,
    )

    print("")
    print(
        "TikTok OAuth server started:"
    )

    print(
        "http://127.0.0.1:8001"
    )

    print("")
    print(
        "Opening TikTok authorization..."
    )

    webbrowser.open(
        auth_url
    )

    server.handle_request()
    server.server_close()

    if "error" in result:
        raise RuntimeError(
            "TikTok authorization failed: "
            f"{result['error']}"
        )

    token_data = result[
        "token_data"
    ]

    print("")
    print(
        "TikTok authorization successful"
    )

    print(
        f"Open ID: "
        f"{token_data.get('open_id')}"
    )

    print(
        f"Scopes: "
        f"{token_data.get('scope')}"
    )

    return token_data