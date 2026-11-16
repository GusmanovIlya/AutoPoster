from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

CLIENT_SECRET_FILE = Path(
    "secrets/youtube_client_secret.json"
)

TOKEN_FILE = Path(
    "secrets/youtube_token.json"
)


def get_youtube_credentials() -> Credentials:
    credentials = None

    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES,
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        if not CLIENT_SECRET_FILE.exists():
            raise FileNotFoundError(
                f"YouTube client secret not found: "
                f"{CLIENT_SECRET_FILE}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES,
        )

        credentials = flow.run_local_server(
            port=0,
            open_browser=True,
        )

    TOKEN_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    TOKEN_FILE.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )

    return credentials