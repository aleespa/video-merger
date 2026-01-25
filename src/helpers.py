import os
import subprocess
from datetime import datetime, timezone


def escape_drawtext(text: str):
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace(" ", "\\ ")
        .replace("'", "\\'")
    )


def get_creation_date(
    path: str,
    source_tz=timezone.utc,
    target_tz=timezone.utc,
) -> datetime:
    try:
        result = (
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format_tags=creation_time",
                    "-of",
                    "default=nw=1:nk=1",
                    path,
                ]
            )
            .decode()
            .strip()
        )

        if result:
            dt = datetime.fromisoformat(result.replace("Z", "+00:00"))

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=source_tz)

            return dt.astimezone(target_tz)

    except Exception:
        pass

    dt = datetime.fromtimestamp(os.path.getmtime(path), tz=target_tz)
    return dt.astimezone(target_tz)


def format_date(dt: datetime, date_format="%Y-%m-%d %H:%M"):
    return dt.strftime(date_format)
