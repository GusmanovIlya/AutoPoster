import json
from pathlib import Path

import requests


TOKEN_FILE = Path("secrets/tiktok_token.json")

BASE_URL = "https://open.tiktokapis.com"


class TikTokClient:

    def __init__(self):
        if not TOKEN_FILE.exists():
            raise FileNotFoundError(
                "TikTok token not found: "
                "secrets/tiktok_token.json"
            )

        token_data = json.loads(
            TOKEN_FILE.read_text(
                encoding="utf-8"
            )
        )

        self.access_token = token_data.get(
            "access_token"
        )

        if not self.access_token:
            raise ValueError(
                "TikTok access_token is missing"
            )

    def get_creator_info(self) -> dict:
        response = requests.post(
            f"{BASE_URL}/v2/post/publish/creator_info/query/",
            headers={
                "Authorization":
                    f"Bearer {self.access_token}",
                "Content-Type":
                    "application/json; charset=UTF-8",
            },
            timeout=30,
        )

        try:
            result = response.json()

        except ValueError:
            raise RuntimeError(
                "TikTok returned invalid JSON: "
                f"{response.text}"
            )

        error = result.get(
            "error",
            {}
        )

        if (
            not response.ok
            or error.get("code") != "ok"
        ):
            raise RuntimeError(
                f"TikTok API error: {result}"
            )

        return result["data"]