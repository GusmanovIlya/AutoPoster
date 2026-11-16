# AutoPoster

Python-проект для публикации текстов, фотографий и видео в социальных сетях. Содержит адаптеры Telegram, VK, Instagram, YouTube и TikTok, общую модель публикации и подготовку вертикальных видео через FFmpeg.

## Структура

```text
app/
├── config/        # Настройки из .env
├── core/          # Общий интерфейс Publisher
├── models/        # Post и MediaType
├── platforms/     # Адаптеры платформ, OAuth и DebugPublisher
└── services/      # Обработка видео
main.py            # Пример публикации видео в TikTok
requirements.txt   # Python-зависимости
.env.example       # Шаблон настроек без секретов
```

## Установка

Требуются Python 3.10+ и, для обработки видео, FFmpeg с ffprobe в PATH.

```bash
git clone git@github.com:GusmanovIlya/AutoPoster.git
cd AutoPoster
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
mkdir -p media secrets logs
```

Заполните в `.env` параметры только тех платформ, которые планируете использовать. Файл `.env`, OAuth-токены из `secrets/`, локальные медиа и журналы не входят в репозиторий.

## Проверка без публикации

Выполните из корня проекта:

```bash
python - <<'PY'
from app.models.post import Post
from app.platforms.debug.publisher import DebugPublisher

DebugPublisher().publish(Post(title="Проверка", text="AutoPoster готов к настройке"))
PY
```

`DebugPublisher` только выводит содержимое поста в терминал.

## Публикация

Выберите нужный адаптер из `app/platforms/` и создайте `Post` с подходящим `MediaType`. Поддержка типов контента зависит от адаптера; наличие кода интеграции не означает, что доступ к API платформы уже настроен.

Текущий `main.py` — пример **реальной публикации в TikTok**, а не пробный запуск. Он использует `media/test.mp4` и требует настроенной авторизации. Изучите и измените пример под свою задачу перед выполнением `python main.py`.

OAuth-помощники находятся в `app/platforms/{instagram,tiktok,youtube}/auth.py`. YouTube ожидает клиентский OAuth JSON в `secrets/youtube_client_secret.json`; токены сохраняются в `secrets/`. Instagram использует публичный URL медиа из `INSTAGRAM_PUBLIC_BASE_URL`. Для доступа к платформам нужны собственные учётные данные, разрешения и корректно настроенные callback-адреса.

## Обработка видео

`app/services/video_processor.py` содержит подготовку Instagram Reels и YouTube Shorts. Обработанные файлы сохраняются в `media/processed/`. Исходное видео нужно добавить локально: медиафайлы не загружаются в Git.

Проект находится в разработке. Расписание и единая команда массовой публикации в текущей версии не реализованы.
