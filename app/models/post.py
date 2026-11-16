from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class MediaType(str, Enum):
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"


@dataclass
class Post:
    text: str = ""
    media_path: Path | None = None
    media_type: MediaType = MediaType.TEXT
    title: str | None = None

    # Если True — перед загрузкой проверяем требования Shorts
    is_short: bool = False