import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from zoneinfo import ZoneInfo, available_timezones

from loguru import logger

from src.settings import Settings
from src.video import get_videos_dates, get_filter_graph, run_ffmpeg


class TkinterSink:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)
        self.text_widget.update_idletasks()


logger.add("logs/log.txt", rotation="10 MB")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Scripting UI")

        # Create input fields
        self.entries = {}

        row = 0

        # Input Files
        tk.Label(root, text="Input Files:").grid(row=row, column=0, sticky="e")
        self.input_files_var = tk.StringVar(value="")
        tk.Entry(root, textvariable=self.input_files_var, width=50).grid(
            row=row, column=1
        )
        tk.Button(root, text="Browse", command=self.browse_input).grid(
            row=row, column=2
        )
        row += 1

        # Output Folder
        tk.Label(root, text="Output Folder:").grid(row=row, column=0, sticky="e")
        self.output_folder_var = tk.StringVar(value="outputs")
        tk.Entry(root, textvariable=self.output_folder_var, width=50).grid(
            row=row, column=1
        )
        tk.Button(root, text="Browse", command=self.browse_output).grid(
            row=row, column=2
        )
        row += 1

        # Output File Name
        tk.Label(root, text="Output File Name:").grid(row=row, column=0, sticky="e")
        self.output_file_name_var = tk.StringVar(value="output.mp4")
        tk.Entry(root, textvariable=self.output_file_name_var, width=50).grid(
            row=row, column=1
        )
        row += 1

        # Font Path
        tk.Label(root, text="Font File:").grid(row=row, column=0, sticky="e")
        self.font_var = tk.StringVar(value="fonts/NotoSans_Condensed-Medium.ttf")
        tk.Entry(root, textvariable=self.font_var, width=50).grid(row=row, column=1)
        tk.Button(root, text="Browse", command=self.browse_font).grid(row=row, column=2)
        row += 1

        # Font Size
        tk.Label(root, text="Font Size:").grid(row=row, column=0, sticky="e")
        self.font_size_var = tk.IntVar(value=52)
        tk.Entry(root, textvariable=self.font_size_var, width=10).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        # Date X Offset
        tk.Label(root, text="Date X Offset:").grid(row=row, column=0, sticky="e")
        self.date_x_offset_var = tk.IntVar(value=40)
        tk.Entry(root, textvariable=self.date_x_offset_var, width=10).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        # Date Y Offset
        tk.Label(root, text="Date Y Offset:").grid(row=row, column=0, sticky="e")
        self.date_y_offset_var = tk.IntVar(value=40)
        tk.Entry(root, textvariable=self.date_y_offset_var, width=10).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        # Font Color
        tk.Label(root, text="Font Color:").grid(row=row, column=0, sticky="e")
        self.font_color_var = tk.StringVar(value="white")
        tk.Entry(root, textvariable=self.font_color_var, width=10).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        # Fade Duration
        tk.Label(root, text="Fade Duration (s):").grid(row=row, column=0, sticky="e")
        self.fade_duration_var = tk.DoubleVar(value=1.0)
        tk.Entry(root, textvariable=self.fade_duration_var, width=10).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        # Timezones
        timezones = sorted(list(available_timezones()))

        tk.Label(root, text="Source Timezone:").grid(row=row, column=0, sticky="e")
        self.source_tz_var = tk.StringVar(value="Europe/London")
        tk.OptionMenu(root, self.source_tz_var, *timezones).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        tk.Label(root, text="Target Timezone:").grid(row=row, column=0, sticky="e")
        self.target_tz_var = tk.StringVar(value="Europe/London")
        tk.OptionMenu(root, self.target_tz_var, *timezones).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        # Run Button
        (
            tk.Button(
                root,
                text="Merge videos",
                command=self.run_program,
                bg="#044011",
                fg="white",
                font=("Arial", 12, "bold"),
            ).grid(row=row, column=0, columnspan=3, pady=20)
        )
        row += 1

        # Log Box
        tk.Label(root, text="Logs:").grid(row=row, column=0, sticky="nw")
        self.log_text = scrolledtext.ScrolledText(root, height=10, width=80)
        self.log_text.grid(row=row, column=1, columnspan=2, sticky="we")
        row += 1

        # Configure logguru to use the text widget
        logger.add(
            TkinterSink(self.log_text).write,
            format="{time:HH:mm:ss} | {level: <8} | {message}",
            colorize=False,
        )

    def browse_input(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Video files", "*.mp4 *.mov *.mxf *.mkv")]
        )
        if files:
            # We store them as a semicolon-separated string in the entry for visibility
            self.input_files_var.set(";".join(files))

    def browse_output(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_folder_var.set(directory)

    def browse_font(self):
        file = filedialog.askopenfilename(filetypes=[("Font files", "*.ttf *.otf")])
        if file:
            self.font_var.set(file)

    def run_program(self):
        try:
            self.log_text.delete(1.0, tk.END)  # Clear logs before new run

            input_files_str = self.input_files_var.get()
            if not input_files_str:
                raise ValueError("No input files selected")

            input_files = input_files_str.split(";")

            settings = Settings(
                input_files=input_files,
                output_folder=self.output_folder_var.get(),
                output_file_name=self.output_file_name_var.get(),
                font=self.font_var.get(),
                font_size=self.font_size_var.get(),
                date_x_offset=self.date_x_offset_var.get(),
                date_y_offset=self.date_y_offset_var.get(),
                font_color=self.font_color_var.get(),
                fade_duration=self.fade_duration_var.get(),
                source_tz=ZoneInfo(self.source_tz_var.get()),
                target_tz=ZoneInfo(self.target_tz_var.get()),
            )

            files, dates = get_videos_dates(settings)
            filter_complex, current_v, current_a = get_filter_graph(
                files, dates, settings
            )
            run_ffmpeg(filter_complex, current_v, current_a, files, settings)

            logger.success("Done!")
            messagebox.showinfo("Success", "Video processing completed successfully!")
        except Exception as e:
            logger.error(f"Error: {e}")
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
