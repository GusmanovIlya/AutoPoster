import json
import subprocess
from pathlib import Path

import requests

from app.config.settings import settings
from app.core.publisher import Publisher
from app.models.post import MediaType, Post


class TelegramPublisher(Publisher):

    def __init__(self):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured")

        if not settings.TELEGRAM_CHAT_ID:
            raise ValueError("TELEGRAM_CHAT_ID is not configured")

        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = (
            f"https://api.telegram.org/"
            f"bot{settings.TELEGRAM_BOT_TOKEN}"
        )

    def publish(self, post: Post) -> None:
        if post.media_type == MediaType.TEXT:
            self._send_text(post)

        elif post.media_type == MediaType.PHOTO:
            self._send_photo(post)

        elif post.media_type == MediaType.VIDEO:
            self._send_video(post)

        else:
            raise ValueError(
                f"Unsupported media type: {post.media_type}"
            )

    def _send_text(self, post: Post) -> None:
        response = requests.post(
            f"{self.base_url}/sendMessage",
            data={
                "chat_id": self.chat_id,
                "text": post.text,
            },
            timeout=30,
        )

        self._check_response(response)

    def _send_photo(self, post: Post) -> None:
        media_path = self._validate_media(post.media_path)

        with media_path.open("rb") as file:
            response = requests.post(
                f"{self.base_url}/sendPhoto",
                data={
                    "chat_id": self.chat_id,
                    "caption": post.text,
                },
                files={
                    "photo": file,
                },
                timeout=60,
            )

        self._check_response(response)

    def _send_video(self, post: Post) -> None:
        media_path = self._validate_media(post.media_path)

        width, height = self._get_video_size(media_path)

        print(f"Video size: {width}x{height}")

        with media_path.open("rb") as file:
            response = requests.post(
                f"{self.base_url}/sendVideo",
                data={
                    "chat_id": self.chat_id,
                    "caption": post.text,
                    "width": width,
                    "height": height,
                    "supports_streaming": "true",
                },
                files={
                    "video": file,
                },
                timeout=120,
            )

        self._check_response(response)

    @staticmethod
    def _validate_media(media_path: Path | None) -> Path:
        if media_path is None:
            raise ValueError("Media path is required")

        if not media_path.exists():
            raise FileNotFoundError(
                f"Media file not found: {media_path}"
            )

        if not media_path.is_file():
            raise ValueError(
                f"Media path is not a file: {media_path}"
            )

        return media_path

    @staticmethod
    def _get_video_size(video_path: Path) -> tuple[int, int]:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=width,height",
                    "-of",
                    "json",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

        except FileNotFoundError:
            raise RuntimeError(
                "ffprobe не найден. Установи ffmpeg: brew install ffmpeg"
            )

        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                f"Не удалось прочитать параметры видео: {error.stderr}"
            )

        data = json.loads(result.stdout)

        streams = data.get("streams", [])

        if not streams:
            raise RuntimeError(
                f"В файле не найден видеопоток: {video_path}"
            )

        width = streams[0].get("width")
        height = streams[0].get("height")

        if not width or not height:
            raise RuntimeError(
                f"Не удалось определить размер видео: {video_path}"
            )

        return width, height

    @staticmethod
    def _check_response(response: requests.Response) -> None:
        if not response.ok:
            raise RuntimeError(
                f"Telegram API error "
                f"[{response.status_code}]: {response.text}"
            )