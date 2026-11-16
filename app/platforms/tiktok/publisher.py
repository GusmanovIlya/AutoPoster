import json
import math
import mimetypes
import time
from pathlib import Path

import requests

from app.core.publisher import Publisher
from app.models.post import MediaType, Post


TOKEN_FILE = Path("secrets/tiktok_token.json")

BASE_URL = "https://open.tiktokapis.com"

MIN_CHUNK_SIZE = 5 * 1024 * 1024
MAX_CHUNK_SIZE = 64 * 1024 * 1024


class TikTokPublisher(Publisher):

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

    def publish(self, post: Post) -> None:
        if post.media_type != MediaType.VIDEO:
            raise NotImplementedError(
                "TikTok publisher currently "
                "supports video only"
            )

        video_path = self._validate_video(
            post.media_path
        )

        creator = self._get_creator_info()

        privacy_level = self._choose_privacy(
            creator
        )

        print("")
        print(
            f"TikTok creator: "
            f"{creator.get('creator_username')}"
        )

        print(
            f"TikTok privacy: "
            f"{privacy_level}"
        )

        max_duration = creator.get(
            "max_video_post_duration_sec"
        )

        if max_duration:
            print(
                f"TikTok max duration: "
                f"{max_duration} sec"
            )

        publish_id, upload_url = (
            self._initialize_upload(
                post=post,
                video_path=video_path,
                privacy_level=privacy_level,
            )
        )

        print(
            f"TikTok publish ID: "
            f"{publish_id}"
        )

        print(
            "TikTok: uploading video..."
        )

        self._upload_video(
            upload_url=upload_url,
            video_path=video_path,
        )

        print(
            "TikTok: upload completed"
        )

        self._wait_for_publish(
            publish_id
        )

    def _get_creator_info(self) -> dict:
        response = requests.post(
            f"{BASE_URL}"
            "/v2/post/publish/"
            "creator_info/query/",
            headers=self._headers(),
            timeout=30,
        )

        result = self._handle_api_response(
            response
        )

        return result["data"]

    def _choose_privacy(
        self,
        creator: dict,
    ) -> str:

        options = creator.get(
            "privacy_level_options",
            [],
        )

        if "SELF_ONLY" in options:
            return "SELF_ONLY"

        if not options:
            raise RuntimeError(
                "TikTok did not return "
                "privacy options"
            )

        return options[0]

    def _initialize_upload(
        self,
        post: Post,
        video_path: Path,
        privacy_level: str,
    ) -> tuple[str, str]:

        file_size = video_path.stat().st_size

        chunk_size = self._calculate_chunk_size(
            file_size
        )

        total_chunks = math.ceil(
            file_size / chunk_size
        )

        caption = post.text.strip()

        if not caption and post.title:
            caption = post.title.strip()

        payload = {
            "post_info": {
                "title": caption,
                "privacy_level": privacy_level,

                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,

                # Сейчас тестируем обычный
                # пользовательский контент.
                "brand_content_toggle": False,
                "brand_organic_toggle": False,

                "is_aigc": False,
            },

            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks,
            },
        }

        print(
            "TikTok: initializing Direct Post..."
        )

        response = requests.post(
            f"{BASE_URL}"
            "/v2/post/publish/video/init/",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )

        result = self._handle_api_response(
            response
        )

        data = result.get(
            "data",
            {}
        )

        publish_id = data.get(
            "publish_id"
        )

        upload_url = data.get(
            "upload_url"
        )

        if not publish_id:
            raise RuntimeError(
                "TikTok did not return "
                "publish_id"
            )

        if not upload_url:
            raise RuntimeError(
                "TikTok did not return "
                "upload_url"
            )

        return (
            publish_id,
            upload_url,
        )

    def _upload_video(
        self,
        upload_url: str,
        video_path: Path,
    ) -> None:

        file_size = video_path.stat().st_size

        chunk_size = self._calculate_chunk_size(
            file_size
        )

        mime_type = (
            mimetypes.guess_type(
                video_path.name
            )[0]
            or "video/mp4"
        )

        start = 0

        with video_path.open("rb") as file:
            while start < file_size:

                remaining = (
                    file_size - start
                )

                current_size = min(
                    chunk_size,
                    remaining,
                )

                data = file.read(
                    current_size
                )

                end = (
                    start
                    + len(data)
                    - 1
                )

                response = requests.put(
                    upload_url,
                    headers={
                        "Content-Type":
                            mime_type,

                        "Content-Length":
                            str(len(data)),

                        "Content-Range":
                            (
                                f"bytes "
                                f"{start}-{end}/"
                                f"{file_size}"
                            ),
                    },
                    data=data,
                    timeout=300,
                )

                if response.status_code not in {
                    201,
                    206,
                }:
                    raise RuntimeError(
                        "TikTok video upload "
                        f"failed "
                        f"[{response.status_code}]: "
                        f"{response.text}"
                    )

                progress = int(
                    ((end + 1) / file_size)
                    * 100
                )

                print(
                    f"TikTok upload: "
                    f"{progress}%"
                )

                start = end + 1

    def _wait_for_publish(
        self,
        publish_id: str,
        timeout: int = 300,
        interval: int = 5,
    ) -> None:

        print(
            "TikTok: waiting for processing..."
        )

        started_at = time.time()

        while True:
            response = requests.post(
                f"{BASE_URL}"
                "/v2/post/publish/"
                "status/fetch/",
                headers=self._headers(),
                json={
                    "publish_id":
                        publish_id
                },
                timeout=30,
            )

            result = self._handle_api_response(
                response
            )

            data = result.get(
                "data",
                {}
            )

            status = data.get(
                "status"
            )

            print(
                f"TikTok processing: "
                f"{status}"
            )

            if status == "PUBLISH_COMPLETE":
                print("")
                print(
                    "TikTok: published "
                    "successfully"
                )

                post_ids = data.get(
                    "publicaly_available_post_id",
                    [],
                )

                if post_ids:
                    print(
                        f"TikTok Post ID: "
                        f"{post_ids[0]}"
                    )

                return

            if status == "FAILED":
                raise RuntimeError(
                    "TikTok publish failed: "
                    f"{data.get('fail_reason')}"
                )

            if (
                time.time()
                - started_at
                > timeout
            ):
                raise TimeoutError(
                    "TikTok publish timeout"
                )

            time.sleep(
                interval
            )

    @staticmethod
    def _calculate_chunk_size(
        file_size: int,
    ) -> int:

        if file_size < MIN_CHUNK_SIZE:
            return file_size

        if file_size <= MAX_CHUNK_SIZE:
            return file_size

        return MAX_CHUNK_SIZE

    def _headers(self) -> dict:
        return {
            "Authorization":
                f"Bearer {self.access_token}",

            "Content-Type":
                "application/json; "
                "charset=UTF-8",
        }

    @staticmethod
    def _handle_api_response(
        response: requests.Response,
    ) -> dict:

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

        error_code = error.get(
            "code"
        )

        if (
            not response.ok
            or error_code != "ok"
        ):
            raise RuntimeError(
                f"TikTok API error: "
                f"{result}"
            )

        return result

    @staticmethod
    def _validate_video(
        media_path: Path | None,
    ) -> Path:

        if media_path is None:
            raise ValueError(
                "TikTok video path "
                "is required"
            )

        if not media_path.exists():
            raise FileNotFoundError(
                f"Video not found: "
                f"{media_path}"
            )

        if not media_path.is_file():
            raise ValueError(
                f"Video path is not a file: "
                f"{media_path}"
            )

        if media_path.suffix.lower() not in {
            ".mp4",
            ".mov",
            ".webm",
        }:
            raise ValueError(
                "TikTok video must be "
                "MP4, MOV or WebM"
            )

        return media_path