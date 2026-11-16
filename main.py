from pathlib import Path

from app.models.post import (
    MediaType,
    Post,
)

from app.platforms.tiktok.publisher import (
    TikTokPublisher,
)


def main():
    post = Post(
        title="TikTok test",
        text="Первое видео через AutoPostSMM",
        media_path=Path(
            "media/test.mp4"
        ),
        media_type=MediaType.VIDEO,
    )

    publisher = TikTokPublisher()

    publisher.publish(
        post
    )


if __name__ == "__main__":
    main()