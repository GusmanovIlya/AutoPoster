import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    # App
    APP_ENV = os.getenv("APP_ENV", "development")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # VK
    VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN")
    VK_GROUP_ID = os.getenv("VK_GROUP_ID")
    VK_API_VERSION = os.getenv("VK_API_VERSION", "5.199")

    # VK app credentials
    # Пока не используются, но можно оставить на будущее.
    VK_APP_ID = os.getenv("VK_APP_ID")
    VK_CLIENT_SECRET = os.getenv("VK_CLIENT_SECRET")

    # Instagram
    INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID")
    INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET")
    INSTAGRAM_REDIRECT_URI = os.getenv("INSTAGRAM_REDIRECT_URI")

    INSTAGRAM_API_VERSION = os.getenv(
        "INSTAGRAM_API_VERSION",
        "v26.0",
    )

    INSTAGRAM_PUBLIC_BASE_URL = os.getenv(
        "INSTAGRAM_PUBLIC_BASE_URL"
    )

    TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
    TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
    TIKTOK_REDIRECT_URI = os.getenv(
        "TIKTOK_REDIRECT_URI",
        "http://127.0.0.1:8001/tiktok/callback/",
    )

settings = Settings()
