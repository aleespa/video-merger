import os
import subprocess
from datetime import timezone

from loguru import logger

from src.helpers import escape_drawtext, format_date, get_creation_date
from src.settings import Settings

VIDEO_EXTENSIONS = (".mp4", ".mov", ".mxf", ".mkv")


def get_videos_dates(settings: Settings) -> tuple[list, ...]:
    logger.info("Getting videos and their dates.")
    files = [
        os.path.join(settings.input_folder, f)
        for f in os.listdir(settings.input_folder)
        if f.lower().endswith(VIDEO_EXTENSIONS)
    ]

    if not files:
        raise RuntimeError("No video files found")

    files.sort(
        key=lambda x: get_creation_date(x, settings.source_tz, settings.target_tz)
    )
    dates = [
        format_date(get_creation_date(f, settings.source_tz, settings.target_tz))
        for f in files
    ]

    logger.info(f"Found {len(files)} video files.")
    return files, dates


def get_filter_graph(
    files: list,
    dates: list,
    settings: Settings,
):
    logger.info("Generating filter graph.")
    filter_parts = []
    video_labels = []
    audio_labels = []

    for i, (file, date) in enumerate(zip(files, dates)):
        v_label = f"v{i}"
        a_label = f"a{i}"
        safe_text = escape_drawtext(date)
        drawtext = (
            f"drawtext="
            f"fontfile='{settings.font}':"
            f"text='{safe_text}':"
            f"x={settings.date_x_offset}:"
            f"y=h-th-{settings.date_y_offset}:"
            f"fontsize={settings.font_size}:"
            f"fontcolor={settings.font_color}"
        )

        filter_parts.append(f"[{i}:v]{drawtext}[{v_label}]")
        # Ensure audio exists and is in a consistent format for acrossfade
        filter_parts.append(
            f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[{a_label}]"
        )
        video_labels.append(v_label)
        audio_labels.append(a_label)

    current_v = video_labels[0]
    current_a = audio_labels[0]
    offset = 0.0

    for i in range(1, len(video_labels)):
        duration = float(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=nw=1:nk=1",
                    files[i - 1],
                ]
            )
            .decode()
            .strip()
        )

        offset += duration - settings.fade_duration
        out_v = f"xv{i}"
        out_a = f"xa{i}"

        # Video xfade
        filter_parts.append(
            f"[{current_v}][{video_labels[i]}]"
            f"xfade=transition=fade:"
            f"duration={settings.fade_duration}:"
            f"offset={offset}"
            f"[{out_v}]"
        )

        # Audio acrossfade
        # acrossfade works by joining two streams with a fade.
        # The offset for acrossfade is not used in the same way as xfade (it doesn't have an 'offset' parameter in the same sense).
        # Instead, we chain them. acrossfade will shorten the total duration by d.
        filter_parts.append(
            f"[{current_a}][{audio_labels[i]}]"
            f"acrossfade=d={settings.fade_duration}:c1=tri:c2=tri"
            f"[{out_a}]"
        )

        current_v = out_v
        current_a = out_a

    return ";".join(filter_parts), current_v, current_a


def run_ffmpeg(
    filter_complex: list,
    current_v: str,
    current_a: str,
    files: list,
    settings: Settings,
):
    cmd = ["ffmpeg", "-y"]

    for f in files:
        cmd += ["-i", f]

    cmd += [
        "-filter_complex",
        filter_complex,
        "-map",
        f"[{current_v}]",
        "-map",
        f"[{current_a}]",
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p6",
        "-rc",
        "vbr",
        "-cq",
        "18",
        "-b:v",
        "0",
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        settings.output_file_path,
    ]

    logger.info("Running FFmpeg...")
    subprocess.run(cmd, check=True)
