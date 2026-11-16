import json
import secrets
import webbrowser

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from app.config.settings import settings


TOKEN_FILE = Path("secrets/instagram_token.json")

SCOPES = [
    "instagram_business_basic",
    "instagram_business_content_publish",
]


def _exchange_code_for_token(code: str) -> dict:
    response = requests.post(
        "https://api.instagram.com/oauth/access_token",
        files={
            "client_id": (
                None,
                settings.INSTAGRAM_APP_ID,
            ),
            "client_secret": (
                None,
                settings.INSTAGRAM_APP_SECRET,
            ),
            "grant_type": (
                None,
                "authorization_code",
            ),
            "redirect_uri": (
                None,
                settings.INSTAGRAM_REDIRECT_URI,
            ),
            "code": (
                None,
                code,
            ),
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"Instagram token error "
            f"[{response.status_code}]: "
            f"{response.text}"
        )

    data = response.json()

    # Поддерживаем оба варианта ответа Meta
    if "data" in data:
        data = data["data"][0]

    return data


def _exchange_long_lived_token(
    short_token: str,
) -> dict:

    response = requests.get(
        "https://graph.instagram.com/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": settings.INSTAGRAM_APP_SECRET,
            "access_token": short_token,
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"Instagram long-lived token error "
            f"[{response.status_code}]: "
            f"{response.text}"
        )

    return response.json()


def _get_profile(access_token: str) -> dict:
    response = requests.get(
        "https://graph.instagram.com/me",
        params={
            "fields": "id,username,account_type",
            "access_token": access_token,
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"Instagram profile error "
            f"[{response.status_code}]: "
            f"{response.text}"
        )

    return response.json()


def authorize_instagram() -> dict:
    if not settings.INSTAGRAM_APP_ID:
        raise ValueError(
            "INSTAGRAM_APP_ID is not configured"
        )

    if not settings.INSTAGRAM_APP_SECRET:
        raise ValueError(
            "INSTAGRAM_APP_SECRET is not configured"
        )

    if not settings.INSTAGRAM_REDIRECT_URI:
        raise ValueError(
            "INSTAGRAM_REDIRECT_URI is not configured"
        )

    state = secrets.token_urlsafe(32)

    params = {
        "force_reauth": "true",
        "client_id": settings.INSTAGRAM_APP_ID,
        "redirect_uri": settings.INSTAGRAM_REDIRECT_URI,
        "response_type": "code",
        "scope": ",".join(SCOPES),
        "state": state,
    }

    auth_url = (
        "https://www.instagram.com/oauth/authorize?"
        + urlencode(params)
    )

    result = {}

    class CallbackHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            parsed = urlparse(self.path)

            if parsed.path != "/instagram/callback":
                self.send_response(404)
                self.end_headers()
                return

            query = parse_qs(parsed.query)

            if "error" in query:
                result["error"] = query
                self._send_response(
                    "Instagram authorization failed."
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

                self._send_response(
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

                self._send_response(
                    "Authorization code not found."
                )
                return

            try:
                print(
                    "Instagram: authorization code received"
                )

                short_data = (
                    _exchange_code_for_token(code)
                )

                short_token = short_data[
                    "access_token"
                ]

                print(
                    "Instagram: short-lived token received"
                )

                long_data = (
                    _exchange_long_lived_token(
                        short_token
                    )
                )

                long_token = long_data[
                    "access_token"
                ]

                print(
                    "Instagram: long-lived token received"
                )

                profile = _get_profile(
                    long_token
                )

                token_data = {
                    "access_token": long_token,
                    "expires_in": long_data.get(
                        "expires_in"
                    ),
                    "user_id": profile.get("id"),
                    "username": profile.get(
                        "username"
                    ),
                    "account_type": profile.get(
                        "account_type"
                    ),
                }

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

                result["token_data"] = token_data

                self._send_response(
                    "Instagram authorization successful. "
                    "You can close this tab."
                )

            except Exception as error:
                result["error"] = str(error)

                print(
                    f"Instagram auth error: {error}"
                )

                self._send_response(
                    "Instagram authorization failed. "
                    "Check the terminal."
                )

        def _send_response(
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
            self.wfile.write(body)

        def log_message(
            self,
            format,
            *args,
        ):
            pass

    print("")
    print("Instagram OAuth server started")
    print("Local: http://localhost:8000")
    print("")
    print("Opening Instagram authorization...")
    print("")

    server = HTTPServer(
        ("0.0.0.0", 8000),
        CallbackHandler,
    )

    webbrowser.open(auth_url)

    server.handle_request()
    server.server_close()

    if "error" in result:
        raise RuntimeError(
            f"Instagram authorization failed: "
            f"{result['error']}"
        )

    return result["token_data"]