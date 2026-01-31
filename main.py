import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox
from zoneinfo import ZoneInfo, available_timezones
import customtkinter as ctk
from loguru import logger

from src.settings import Settings
from src.video import get_videos_dates, get_filter_graph, run_ffmpeg

ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue")


class TkinterSink:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")
        self.text_widget.update_idletasks()


logger.add("logs/log.txt", rotation="10 MB")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Video Scripting UI")
        self.geometry("900x750")

        # Configure grid layout (1x2)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Title
        self.label_title = ctk.CTkLabel(
            self.main_frame,
            text="Video Scripting",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.label_title.grid(row=row, column=0, columnspan=3, pady=(0, 20))
        row += 1

        # Input Files
        ctk.CTkLabel(self.main_frame, text="Input Files:").grid(
            row=row, column=0, padx=10, pady=5, sticky="e"
        )
        self.input_files_var = tk.StringVar(value="")
        self.input_files_entry = ctk.CTkEntry(
            self.main_frame, textvariable=self.input_files_var
        )
        self.input_files_entry.grid(row=row, column=1, padx=10, pady=5, sticky="we")
        ctk.CTkButton(
            self.main_frame, text="Browse", width=100, command=self.browse_input
        ).grid(row=row, column=2, padx=10, pady=5)
        row += 1

        # Output Folder
        ctk.CTkLabel(self.main_frame, text="Output Folder:").grid(
            row=row, column=0, padx=10, pady=5, sticky="e"
        )
        self.output_folder_var = tk.StringVar(value="outputs")
        self.output_folder_entry = ctk.CTkEntry(
            self.main_frame, textvariable=self.output_folder_var
        )
        self.output_folder_entry.grid(row=row, column=1, padx=10, pady=5, sticky="we")
        ctk.CTkButton(
            self.main_frame, text="Browse", width=100, command=self.browse_output
        ).grid(row=row, column=2, padx=10, pady=5)
        row += 1

        # Output File Name
        ctk.CTkLabel(self.main_frame, text="Output File Name:").grid(
            row=row, column=0, padx=10, pady=5, sticky="e"
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file_name_var = tk.StringVar(value=f"video_{timestamp}.mp4")
        self.output_file_name_entry = ctk.CTkEntry(
            self.main_frame, textvariable=self.output_file_name_var
        )
        self.output_file_name_entry.grid(
            row=row, column=1, padx=10, pady=5, sticky="we"
        )
        row += 1

        # Font Path
        self.font_var = tk.StringVar(value="fonts/NotoSans_Condensed-Medium.ttf")

        # Options variables
        self.font_size_var = tk.IntVar(value=52)
        self.date_x_offset_var = tk.IntVar(value=40)
        self.date_y_offset_var = tk.IntVar(value=40)
        self.font_color_var = tk.StringVar(value="white")
        self.fade_duration_var = tk.DoubleVar(value=1.0)

        # Timezones variables
        self.source_tz_var = tk.StringVar(value="Europe/London")
        self.target_tz_var = tk.StringVar(value="Europe/London")

        # Date Label Options Button
        self.options_button = ctk.CTkButton(
            self.main_frame,
            text="Date label options",
            command=self.open_options,
        )
        self.options_button.grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        # Run Button
        self.run_button = ctk.CTkButton(
            self.main_frame,
            text="Merge Videos",
            command=self.run_program,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40,
            fg_color="#2c8c3a",
            hover_color="#23702e",
        )
        self.run_button.grid(row=row, column=0, columnspan=3, pady=20, sticky="we")
        row += 1

        # Log Box
        ctk.CTkLabel(self.main_frame, text="Logs:", font=ctk.CTkFont(weight="bold")).grid(
            row=row, column=0, padx=10, pady=(10, 0), sticky="nw"
        )
        row += 1
        self.log_text = ctk.CTkTextbox(self.main_frame, height=200)
        self.log_text.grid(
            row=row, column=0, columnspan=3, padx=10, pady=5, sticky="nsew"
        )
        self.main_frame.grid_rowconfigure(row, weight=1)
        self.log_text.configure(state="disabled")

        # Configure logguru to use the text widget
        logger.add(
            TkinterSink(self.log_text).write,
            format="{time:HH:mm:ss} | {level: <8} | {message}",
            colorize=False,
        )

    def open_options(self):
        if hasattr(self, "options_window") and self.options_window.winfo_exists():
            self.options_window.focus()
            return

        self.options_window = ctk.CTkToplevel(self)
        self.options_window.title("Date Label Options")
        self.options_window.geometry("600x400")
        self.options_window.grid_columnconfigure(0, weight=1)
        self.options_window.grid_rowconfigure(0, weight=1)

        # Ensure the window is on top
        self.options_window.attributes("-topmost", True)

        options_main_frame = ctk.CTkFrame(self.options_window)
        options_main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        options_main_frame.grid_columnconfigure(1, weight=1)

        row = 0
        # Font Path
        ctk.CTkLabel(options_main_frame, text="Font File:").grid(
            row=row, column=0, padx=10, pady=5, sticky="e"
        )
        self.font_entry = ctk.CTkEntry(options_main_frame, textvariable=self.font_var)
        self.font_entry.grid(row=row, column=1, padx=10, pady=5, sticky="we")
        ctk.CTkButton(
            options_main_frame, text="Browse", width=100, command=self.browse_font
        ).grid(row=row, column=2, padx=10, pady=5)
        row += 1

        # Options Frame
        self.options_frame = ctk.CTkFrame(options_main_frame, fg_color="transparent")
        self.options_frame.grid(
            row=row, column=0, columnspan=3, padx=0, pady=10, sticky="we"
        )
        self.options_frame.grid_columnconfigure((1, 3, 5), weight=1)

        # Font Size
        ctk.CTkLabel(self.options_frame, text="Font Size:").grid(
            row=0, column=0, padx=10, pady=5, sticky="e"
        )
        ctk.CTkEntry(self.options_frame, textvariable=self.font_size_var, width=60).grid(
            row=0, column=1, padx=10, pady=5, sticky="w"
        )

        # Date X Offset
        ctk.CTkLabel(self.options_frame, text="X Offset:").grid(
            row=0, column=2, padx=10, pady=5, sticky="e"
        )
        ctk.CTkEntry(
            self.options_frame, textvariable=self.date_x_offset_var, width=60
        ).grid(row=0, column=3, padx=10, pady=5, sticky="w")

        # Date Y Offset
        ctk.CTkLabel(self.options_frame, text="Y Offset:").grid(
            row=0, column=4, padx=10, pady=5, sticky="e"
        )
        ctk.CTkEntry(
            self.options_frame, textvariable=self.date_y_offset_var, width=60
        ).grid(row=0, column=5, padx=10, pady=5, sticky="w")

        # Font Color
        ctk.CTkLabel(self.options_frame, text="Font Color:").grid(
            row=1, column=0, padx=10, pady=5, sticky="e"
        )
        ctk.CTkEntry(
            self.options_frame, textvariable=self.font_color_var, width=100
        ).grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Fade Duration
        ctk.CTkLabel(self.options_frame, text="Fade (s):").grid(
            row=1, column=2, padx=10, pady=5, sticky="e"
        )
        ctk.CTkEntry(
            self.options_frame, textvariable=self.fade_duration_var, width=60
        ).grid(row=1, column=3, padx=10, pady=5, sticky="w")

        row += 1

        # Timezones
        timezones = sorted(list(available_timezones()))

        self.tz_frame = ctk.CTkFrame(options_main_frame, fg_color="transparent")
        self.tz_frame.grid(row=row, column=0, columnspan=3, padx=0, pady=10, sticky="we")
        self.tz_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(self.tz_frame, text="Source TZ:").grid(
            row=0, column=0, padx=10, pady=5, sticky="e"
        )
        self.source_tz_menu = ctk.CTkOptionMenu(
            self.tz_frame, values=timezones, variable=self.source_tz_var
        )
        self.source_tz_menu.grid(row=0, column=1, padx=10, pady=5, sticky="we")

        ctk.CTkLabel(self.tz_frame, text="Target TZ:").grid(
            row=0, column=2, padx=10, pady=5, sticky="e"
        )
        self.target_tz_menu = ctk.CTkOptionMenu(
            self.tz_frame, values=timezones, variable=self.target_tz_var
        )
        self.target_tz_menu.grid(row=0, column=3, padx=10, pady=5, sticky="we")

    def browse_input(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Video files", "*.mp4 *.mov *.mxf *.mkv")]
        )
        if files:
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
        def worker():
            try:
                input_files_str = self.input_files_var.get()
                if not input_files_str:
                    raise ValueError("No input files selected")

                input_files = input_files_str.split(";")

                output_file_name = self.output_file_name_var.get()
                if not output_file_name.lower().endswith(".mp4"):
                    output_file_name += ".mp4"

                settings = Settings(
                    input_files=input_files,
                    output_folder=self.output_folder_var.get(),
                    output_file_name=output_file_name,
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

                def on_success():
                    self.run_button.configure(state="normal")
                    logger.success("Done!")
                    messagebox.showinfo(
                        "Success", "Video processing completed successfully!"
                    )

                self.after(0, on_success)
            except Exception as e:

                def on_error(err_msg=str(e)):
                    self.run_button.configure(state="normal")
                    logger.error(f"Error: {err_msg}")
                    messagebox.showerror("Error", err_msg)

                self.after(0, on_error)

        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", tk.END)
            self.log_text.configure(state="disabled")

            self.run_button.configure(state="disabled")
            threading.Thread(target=worker, daemon=True).start()
        except Exception as e:
            logger.error(f"Error starting thread: {e}")
            self.run_button.configure(state="normal")
            messagebox.showerror("Error", f"Failed to start processing: {e}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
