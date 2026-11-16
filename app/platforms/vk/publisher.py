import requests

from app.config.settings import settings
from app.core.publisher import Publisher
from app.models.post import MediaType, Post


class VKPublisher(Publisher):

    def __init__(self):
        if not settings.VK_ACCESS_TOKEN:
            raise ValueError("VK_ACCESS_TOKEN is not configured")

        if not settings.VK_GROUP_ID:
            raise ValueError("VK_GROUP_ID is not configured")

        self.access_token = settings.VK_ACCESS_TOKEN
        self.group_id = int(settings.VK_GROUP_ID)
        self.api_version = settings.VK_API_VERSION

        self.base_url = "https://api.vk.com/method"

    def publish(self, post: Post) -> None:
        if post.media_type == MediaType.TEXT:
            self._send_text(post)
            return

        if post.media_type == MediaType.PHOTO:
            raise NotImplementedError(
                "VK photo publishing is unavailable "
                "with the current community token"
            )

        if post.media_type == MediaType.VIDEO:
            raise NotImplementedError(
                "VK video publishing is unavailable "
                "with the current community token"
            )

        raise ValueError(
            f"Unsupported VK media type: {post.media_type}"
        )

    def _send_text(self, post: Post) -> None:
        text = post.text.strip()

        if not text:
            raise ValueError("VK post text is empty")

        result = self._api_call(
            "wall.post",
            {
                "owner_id": -self.group_id,
                "from_group": 1,
                "message": text,
            },
        )

        post_id = result.get("post_id")

        print(
            f"VK: published successfully, "
            f"post_id={post_id}"
        )

    def _api_call(
        self,
        method: str,
        params: dict | None = None,
    ) -> dict:

        params = params or {}

        response = requests.post(
            f"{self.base_url}/{method}",
            data={
                **params,
                "access_token": self.access_token,
                "v": self.api_version,
            },
            timeout=30,
        )

        try:
            data = response.json()

        except ValueError:
            raise RuntimeError(
                f"VK returned invalid JSON "
                f"[HTTP {response.status_code}]: "
                f"{response.text}"
            )

        if "error" in data:
            error = data["error"]

            error_code = error.get("error_code")
            error_message = error.get("error_msg")

            raise RuntimeError(
                f"VK API error "
                f"[{error_code}]: "
                f"{error_message}"
            )

        if "response" not in data:
            raise RuntimeError(
                f"VK API returned unexpected response: {data}"
            )

        return data["response"]