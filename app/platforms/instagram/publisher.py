import json
import time
from pathlib import Path
from urllib.parse import quote

import requests

from app.config.settings import settings
from app.core.publisher import Publisher
from app.models.post import MediaType, Post
from app.services.video_processor import VideoProcessor


TOKEN_FILE = Path("secrets/instagram_token.json")
MEDIA_ROOT = Path("media")


class InstagramPublisher(Publisher):

    def __init__(self):
        if not TOKEN_FILE.exists():
            raise FileNotFoundError(
                "Instagram token not found: "
                "secrets/instagram_token.json"
            )

        token_data = json.loads(
            TOKEN_FILE.read_text(encoding="utf-8")
        )

        self.access_token = token_data.get("access_token")
        self.user_id = token_data.get("user_id")

        if not self.access_token:
            raise ValueError(
                "Instagram access token is missing"
            )

        if not self.user_id:
            raise ValueError(
                "Instagram user ID is missing"
            )

        if not settings.INSTAGRAM_PUBLIC_BASE_URL:
            raise ValueError(
                "INSTAGRAM_PUBLIC_BASE_URL is not configured"
            )

        self.base_url = (
            "https://graph.instagram.com/"
            f"{settings.INSTAGRAM_API_VERSION}"
        )

        self.public_base_url = (
            settings.INSTAGRAM_PUBLIC_BASE_URL.rstrip("/")
        )

        self.video_processor = VideoProcessor()

    def publish(self, post: Post) -> None:
        if post.media_type == MediaType.PHOTO:
            self._send_photo(post)
            return

        if post.media_type == MediaType.VIDEO:
            self._send_reel(post)
            return

        if post.media_type == MediaType.TEXT:
            raise NotImplementedError(
                "Instagram does not support text-only posts"
            )

        raise ValueError(
            f"Unsupported Instagram media type: "
            f"{post.media_type}"
        )

    def _send_photo(self, post: Post) -> None:
        media_path = self._validate_photo(
            post.media_path
        )

        image_url = self._build_public_url(
            media_path
        )

        print(f"Instagram image URL: {image_url}")
        print("Instagram: creating photo container...")

        container = self._api_post(
            f"/{self.user_id}/media",
            {
                "image_url": image_url,
                "caption": post.text,
            },
        )

        creation_id = container.get("id")

        if not creation_id:
            raise RuntimeError(
                f"Instagram did not return creation_id: "
                f"{container}"
            )

        print(
            f"Instagram container created: "
            f"{creation_id}"
        )

        result = self._publish_container(
            creation_id
        )

        print("Instagram photo: published successfully")
        print(
            f"Instagram Media ID: "
            f"{result.get('id')}"
        )

    def _send_reel(self, post: Post) -> None:
        original_path = self._validate_video(
            post.media_path
        )

        # Автоматически приводим видео
        # к безопасному формату Instagram Reel.
        print("Instagram: preparing Reel...")

        media_path = (
            self.video_processor.prepare_instagram_reel(
                original_path
            )
        )

        video_url = self._build_public_url(
            media_path
        )

        print(f"Instagram video URL: {video_url}")

        print(
            "Instagram: checking public video URL..."
        )

        self._check_public_media(video_url)

        print(
            "Instagram: creating Reel container..."
        )

        container = self._api_post(
            f"/{self.user_id}/media",
            {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": post.text,
                "share_to_feed": "true",
            },
        )

        creation_id = container.get("id")

        if not creation_id:
            raise RuntimeError(
                f"Instagram did not return creation_id: "
                f"{container}"
            )

        print(
            f"Instagram Reel container: "
            f"{creation_id}"
        )

        self._wait_until_ready(
            creation_id
        )

        result = self._publish_container(
            creation_id
        )

        print(
            "Instagram Reel: published successfully"
        )

        print(
            f"Instagram Media ID: "
            f"{result.get('id')}"
        )

    def _wait_until_ready(
        self,
        creation_id: str,
        timeout: int = 300,
        interval: int = 5,
    ) -> None:

        print(
            "Instagram: waiting for video processing..."
        )

        started_at = time.time()

        while True:
            result = self._api_get(
                f"/{creation_id}",
                {
                    "fields": "status_code,status",
                },
            )

            status_code = result.get(
                "status_code"
            )

            status_text = result.get(
                "status"
            )

            print(
                f"Instagram processing: "
                f"{status_code}"
            )

            if status_code == "FINISHED":
                print(
                    "Instagram: Reel processing finished"
                )
                return

            if status_code in {
                "ERROR",
                "EXPIRED",
            }:
                raise RuntimeError(
                    "Instagram Reel processing failed. "
                    f"status_code={status_code}, "
                    f"status={status_text}"
                )

            if time.time() - started_at > timeout:
                raise TimeoutError(
                    "Instagram Reel processing timeout"
                )

            time.sleep(interval)

    def _publish_container(
        self,
        creation_id: str,
    ) -> dict:

        print("Instagram: publishing...")

        return self._api_post(
            f"/{self.user_id}/media_publish",
            {
                "creation_id": creation_id,
            },
        )

    def _check_public_media(
        self,
        media_url: str,
    ) -> None:

        response = requests.get(
            media_url,
            stream=True,
            timeout=30,
        )

        try:
            if not response.ok:
                raise RuntimeError(
                    "Public media is unavailable: "
                    f"HTTP {response.status_code}"
                )

            content_type = response.headers.get(
                "Content-Type",
                "",
            )

            print(
                f"Public media Content-Type: "
                f"{content_type}"
            )

        finally:
            response.close()

    def _api_post(
        self,
        endpoint: str,
        data: dict,
    ) -> dict:

        response = requests.post(
            f"{self.base_url}{endpoint}",
            data={
                **data,
                "access_token": self.access_token,
            },
            timeout=60,
        )

        return self._handle_response(
            response
        )

    def _api_get(
        self,
        endpoint: str,
        params: dict,
    ) -> dict:

        response = requests.get(
            f"{self.base_url}{endpoint}",
            params={
                **params,
                "access_token": self.access_token,
            },
            timeout=60,
        )

        return self._handle_response(
            response
        )

    @staticmethod
    def _handle_response(
        response: requests.Response,
    ) -> dict:

        try:
            result = response.json()

        except ValueError:
            raise RuntimeError(
                "Instagram returned invalid JSON: "
                f"{response.text}"
            )

        if not response.ok or "error" in result:
            error = result.get(
                "error",
                result,
            )

            raise RuntimeError(
                f"Instagram API error: {error}"
            )

        return result

    def _build_public_url(
        self,
        media_path: Path,
    ) -> str:

        try:
            relative_path = media_path.relative_to(
                MEDIA_ROOT
            )

        except ValueError:
            raise ValueError(
                "Instagram media must be inside "
                "the media/ directory"
            )

        url_path = quote(
            relative_path.as_posix(),
            safe="/",
        )

        return (
            f"{self.public_base_url}/"
            f"{url_path}"
        )

    @staticmethod
    def _validate_photo(
        media_path: Path | None,
    ) -> Path:

        if media_path is None:
            raise ValueError(
                "Instagram photo path is required"
            )

        if not media_path.exists():
            raise FileNotFoundError(
                f"Photo not found: {media_path}"
            )

        if not media_path.is_file():
            raise ValueError(
                f"Photo path is not a file: "
                f"{media_path}"
            )

        if media_path.suffix.lower() not in {
            ".jpg",
            ".jpeg",
        }:
            raise ValueError(
                "Instagram photo must be JPEG"
            )

        return media_path

    @staticmethod
    def _validate_video(
        media_path: Path | None,
    ) -> Path:

        if media_path is None:
            raise ValueError(
                "Instagram video path is required"
            )

        if not media_path.exists():
            raise FileNotFoundError(
                f"Video not found: {media_path}"
            )

        if not media_path.is_file():
            raise ValueError(
                f"Video path is not a file: "
                f"{media_path}"
            )

        if media_path.suffix.lower() not in {
            ".mp4",
            ".mov",
        }:
            raise ValueError(
                "Instagram Reel must be MP4 or MOV"
            )

        return media_path