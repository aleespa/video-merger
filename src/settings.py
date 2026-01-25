from dataclasses import dataclass
from zoneinfo import ZoneInfo


@dataclass
class Settings:
    input_folder: str
    output_folder: str
    output_file_name: str
    font: str
    font_size: int
    date_x_offset: int
    date_y_offset: int
    font_color: str
    fade_duration: float
    source_tz: ZoneInfo
    target_tz: ZoneInfo

    @property
    def output_file_path(self):
        return f"{self.output_folder}/{self.output_file_name}"
