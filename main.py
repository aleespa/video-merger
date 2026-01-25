import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

INPUT_DIR = "inputs"
OUTPUT_FILE = "outputs/output.mp4"
FONT_FILE = "fonts/NotoSans_Condensed-Medium.ttf"

FONT_SIZE = 52
FONT_COLOR = "white"
X_OFFSET = 40
Y_OFFSET = 40
FADE_DURATION = 1.0  # seconds

VIDEO_EXTS = (".mp4", ".mov", ".mxf", ".mkv")

# Timezone the camera timestamps are RECORDED IN
SOURCE_TIMEZONE = ZoneInfo("Europe/London")
TARGET_TIMEZONE = ZoneInfo("America/Mexico_City")

# Date + time format for overlay
DATE_FORMAT = "%Y-%m-%d %H:%M"

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def escape_drawtext(text):
    return (
        text.replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace(" ", "\\ ")
            .replace("'", "\\'")
    )


def get_creation_date(path):
    try:
        result = subprocess.check_output([
            "ffprobe",
            "-v", "error",
            "-show_entries", "format_tags=creation_time",
            "-of", "default=nw=1:nk=1",
            path
        ]).decode().strip()

        if result:
            dt = datetime.fromisoformat(result.replace("Z", "+00:00"))

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=SOURCE_TIMEZONE)

            return dt.astimezone(TARGET_TIMEZONE)

    except Exception:
        pass

    dt = datetime.fromtimestamp(os.path.getmtime(path), tz=SOURCE_TIMEZONE)
    return dt.astimezone(TARGET_TIMEZONE)


def format_date(dt):
    return dt.strftime(DATE_FORMAT)

# --------------------------------------------------
# INPUT FILES
# --------------------------------------------------

files = [
    os.path.join(INPUT_DIR, f)
    for f in os.listdir(INPUT_DIR)
    if f.lower().endswith(VIDEO_EXTS)
]

if not files:
    raise RuntimeError("No video files found")

files.sort(key=get_creation_date)
dates = [format_date(get_creation_date(f)) for f in files]

# --------------------------------------------------
# FILTER GRAPH
# --------------------------------------------------

filter_parts = []
video_labels = []
audio_labels = []

for i, (file, date) in enumerate(zip(files, dates)):
    v_label = f"v{i}"
    a_label = f"a{i}"
    safe_text = escape_drawtext(date)
    drawtext = (
        f"drawtext="
        f"fontfile='{FONT_FILE}':"
        f"text='{safe_text}':"
        f"x={X_OFFSET}:"
        f"y=h-th-{Y_OFFSET}:"
        f"fontsize={FONT_SIZE}:"
        f"fontcolor={FONT_COLOR}"
    )

    filter_parts.append(f"[{i}:v]{drawtext}[{v_label}]")
    # Ensure audio exists and is in a consistent format for acrossfade
    filter_parts.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[{a_label}]")
    video_labels.append(v_label)
    audio_labels.append(a_label)

current_v = video_labels[0]
current_a = audio_labels[0]
offset = 0.0

for i in range(1, len(video_labels)):
    duration = float(subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1",
        files[i - 1]
    ]).decode().strip())

    offset += duration - FADE_DURATION
    out_v = f"xv{i}"
    out_a = f"xa{i}"

    # Video xfade
    filter_parts.append(
        f"[{current_v}][{video_labels[i]}]"
        f"xfade=transition=fade:"
        f"duration={FADE_DURATION}:"
        f"offset={offset}"
        f"[{out_v}]"
    )

    # Audio acrossfade
    # acrossfade works by joining two streams with a fade. 
    # The offset for acrossfade is not used in the same way as xfade (it doesn't have an 'offset' parameter in the same sense).
    # Instead, we chain them. acrossfade will shorten the total duration by d.
    filter_parts.append(
        f"[{current_a}][{audio_labels[i]}]"
        f"acrossfade=d={FADE_DURATION}:c1=tri:c2=tri"
        f"[{out_a}]"
    )

    current_v = out_v
    current_a = out_a

filter_complex = ";".join(filter_parts)

# --------------------------------------------------
# FFMPEG COMMAND
# --------------------------------------------------

cmd = ["ffmpeg", "-y"]

for f in files:
    cmd += ["-i", f]

cmd += [
    "-filter_complex", filter_complex,
    "-map", f"[{current_v}]",
    "-map", f"[{current_a}]",
    "-c:v", "h264_nvenc",
    "-preset", "p6",
    "-rc", "vbr",
    "-cq", "18",
    "-b:v", "0",
    "-profile:v", "high",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    OUTPUT_FILE
]

print("Running FFmpeg...")
subprocess.run(cmd, check=True)
print("Done:", OUTPUT_FILE)
