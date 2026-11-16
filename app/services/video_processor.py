import json
import subprocess
from pathlib import Path


class VideoProcessor:

    SHORT_WIDTH = 1080
    SHORT_HEIGHT = 1920
    MAX_SHORT_DURATION = 180.0

    def prepare_instagram_reel(
        self,
        video_path: Path,
    ) -> Path:

        if not video_path.exists():
            raise FileNotFoundError(
                f"Video not found: {video_path}"
            )

        output_dir = Path("media/processed")
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = (
            output_dir /
            f"{video_path.stem}_reel.mp4"
        )

        print("Preparing video for Instagram Reel...")

        filter_complex = (
            "[0:v]split=2[bg][fg];"
            "[bg]"
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "boxblur=20:10"
            "[background];"
            "[fg]"
            "scale=1080:1920:"
            "force_original_aspect_ratio=decrease"
            "[foreground];"
            "[background][foreground]"
            "overlay=(W-w)/2:(H-h)/2,"
            "format=yuv420p,"
            "fps=30"
            "[video]"
        )

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(video_path),

                    "-filter_complex",
                    filter_complex,

                    "-map",
                    "[video]",

                    "-map",
                    "0:a?",

                    "-c:v",
                    "libx264",

                    "-profile:v",
                    "high",

                    "-preset",
                    "medium",

                    "-crf",
                    "20",

                    "-maxrate",
                    "8M",

                    "-bufsize",
                    "16M",

                    "-c:a",
                    "aac",

                    "-ar",
                    "48000",

                    "-b:a",
                    "128k",

                    "-movflags",
                    "+faststart",

                    str(output_path),
                ],
                check=True,
            )

        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                f"Instagram Reel conversion failed: {error}"
            )

        print(
            f"Instagram Reel prepared: {output_path}"
        )

        return output_path

    @staticmethod
    def get_video_info(video_path: Path) -> dict:
        if not video_path.exists():
            raise FileNotFoundError(
                f"Video not found: {video_path}"
            )

        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=width,height:format=duration",
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
                "ffprobe not found. Install ffmpeg first."
            )
        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                f"ffprobe error: {error.stderr}"
            )

        data = json.loads(result.stdout)

        streams = data.get("streams", [])

        if not streams:
            raise RuntimeError(
                "Video stream not found"
            )

        stream = streams[0]

        return {
            "width": int(stream["width"]),
            "height": int(stream["height"]),
            "duration": float(data["format"]["duration"]),
        }

    def prepare_short(
        self,
        video_path: Path,
    ) -> Path:

        info = self.get_video_info(video_path)

        width = info["width"]
        height = info["height"]
        duration = info["duration"]

        print(
            f"Video: {width}x{height}, "
            f"{duration:.2f} sec"
        )

        if duration > self.MAX_SHORT_DURATION:
            raise ValueError(
                f"Video is too long for Shorts: "
                f"{duration:.2f} sec"
            )

        # Уже вертикальное или квадратное.
        if width <= height:
            print("Video already suitable for Shorts")
            return video_path

        output_dir = Path("media/processed")
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = (
            output_dir /
            f"{video_path.stem}_short.mp4"
        )

        print("Converting horizontal video to 9:16...")

        filter_complex = (
            "[0:v]scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "boxblur=20:10[background];"
            "[0:v]scale=1080:1920:"
            "force_original_aspect_ratio=decrease[foreground];"
            "[background][foreground]"
            "overlay=(W-w)/2:(H-h)/2"
        )

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(video_path),
                    "-filter_complex",
                    filter_complex,
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "20",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-movflags",
                    "+faststart",
                    str(output_path),
                ],
                check=True,
            )

        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. "
                "Install it with: brew install ffmpeg"
            )

        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                f"Video conversion failed: {error}"
            )

        print(
            f"Short prepared: {output_path}"
        )

        return output_path
