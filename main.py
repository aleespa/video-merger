from zoneinfo import ZoneInfo

from loguru import logger

from src.settings import Settings
from src.video import get_videos_dates, get_filter_graph, run_ffmpeg

logger.add("logs/log.txt", rotation="10 MB")

settings = Settings(
    input_folder="inputs",
    output_folder="outputs",
    output_file_name="output.mp4",
    font="fonts/NotoSans_Condensed-Medium.ttf",
    font_size=52,
    date_x_offset=40,
    date_y_offset=40,
    font_color="white",
    fade_duration=1.0,
    source_tz=ZoneInfo("Europe/London"),
    target_tz=ZoneInfo("Europe/London"),
)

files, dates = get_videos_dates(settings)

filter_complex, current_v, current_a = get_filter_graph(files, dates, settings)

run_ffmpeg(filter_complex, current_v, current_a, files, settings)

logger.success("Done!")
