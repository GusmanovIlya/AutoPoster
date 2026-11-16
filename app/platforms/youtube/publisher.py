from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.core.publisher import Publisher
from app.models.post import MediaType, Post
from app.platforms.youtube.auth import get_youtube_credentials
from app.services.video_processor import VideoProcessor


class YouTubePublisher(Publisher):

    def __init__(self):
        credentials = get_youtube_credentials()

        self.youtube = build(
            "youtube",
            "v3",
            credentials=credentials,
        )

        self.video_processor = VideoProcessor()

    def publish(self, post: Post) -> None:
        if post.media_type != MediaType.VIDEO:
            raise NotImplementedError(
                "YouTube supports only video posts for now"
            )

        self._send_video(post)

    def _send_video(self, post: Post) -> None:
        media_path = self._validate_media(post.media_path)

        # Если это Short — автоматически подготавливаем видео
        if post.is_short:
            print("YouTube: preparing Short...")

            media_path = self.video_processor.prepare_short(
                media_path
            )

        title = (post.title or "Untitled video").strip()
        description = post.text.strip()

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": "private",
            },
        }

        media = MediaFileUpload(
            str(media_path),
            chunksize=8 * 1024 * 1024,
            resumable=True,
        )

        request = self.youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        if post.is_short:
            print("YouTube: uploading Short...")
        else:
            print("YouTube: uploading video...")

        response = None

        while response is None:
            status, response = request.next_chunk()

            if status:
                progress = int(status.progress() * 100)
                print(f"YouTube upload: {progress}%")

        video_id = response["id"]

        print("YouTube: upload completed")
        print(f"Video ID: {video_id}")
        print(
            f"URL: https://www.youtube.com/watch?v={video_id}"
        )

    @staticmethod
    def _validate_media(
        media_path: Path | None,
    ) -> Path:

        if media_path is None:
            raise ValueError(
                "YouTube video path is required"
            )

        if not media_path.exists():
            raise FileNotFoundError(
                f"Video file not found: {media_path}"
            )

        if not media_path.is_file():
            raise ValueError(
                f"Video path is not a file: {media_path}"
            )

        return media_path