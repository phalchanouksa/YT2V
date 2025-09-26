import os
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from config_utils import load_ffmpeg_path, save_ffmpeg_path
from ytdlp_service import (
    fetch_video_info,
    parse_streams,
    ensure_ffmpeg_available,
    build_download_command,
    run_download,
)


class YouTubeDownloader:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("YT2V")
        self.root.geometry("840x560")
        self.root.resizable(False, False)
        self.root.configure(bg='#f0f0f0')

        self.yt_title = ""
        self.yt_streams = []
        self.stream_options = []
        self.ffmpeg_path = tk.StringVar()

        # DPI-aware on Windows for crisp fonts
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # Styles
        style = ttk.Style(self.root)
        font_name = "Segoe UI"
        font_size = 10
        style.configure('.', font=(font_name, font_size))
        style.configure('TButton', padding=6)
        style.configure('TLabel', padding=5)
        style.configure('TCheckbutton', padding=5)

        # UI Elements
        self.url_label = ttk.Label(root, text="YouTube Video URL:", background='#f0f0f0')
        self.url_label.pack(pady=(15, 5))

        self.url_entry = ttk.Entry(root, width=70, font=(font_name, font_size))
        self.url_entry.pack(pady=5, padx=25, ipady=7)

        self.include_high_quality = tk.BooleanVar()
        self.hq_check = ttk.Checkbutton(
            root,
            text="Include High-Quality options (requires FFmpeg)",
            variable=self.include_high_quality
        )
        self.hq_check.pack(pady=8)

        self.fetch_button = ttk.Button(root, text="Fetch Qualities", command=self.start_fetch_thread)
        self.fetch_button.pack(pady=8)

        self.quality_label = ttk.Label(root, text="Select Quality:", background='#f0f0f0')
        self.quality_label.pack(pady=(8, 5))

        self.selected_quality = tk.StringVar()
        self.quality_menu = ttk.OptionMenu(root, self.selected_quality, "No qualities fetched")
        self.quality_menu.pack(pady=5, padx=25, ipady=5)
        self.quality_menu['state'] = 'disabled'

        self.download_button = ttk.Button(root, text="Download", command=self.start_download_thread)
        self.download_button.pack(pady=12)
        self.download_button['state'] = 'disabled'

        self.progress_bar = ttk.Progressbar(root, orient='horizontal', length=700, mode='determinate')
        self.progress_bar.pack(pady=8, padx=25)

        self.status_label = ttk.Label(root, text="", background='#f0f0f0', wraplength=780)
        self.status_label.pack(pady=8)

        # FFmpeg Path Setter
        self.ffmpeg_frame = ttk.Frame(root)
        self.ffmpeg_frame.pack(fill='x', padx=25, pady=(8, 0))
        self.ffmpeg_button = ttk.Button(self.ffmpeg_frame, text="Set FFmpeg Path", command=self.select_ffmpeg_path)
        self.ffmpeg_button.pack(side='left')
        self.ffmpeg_path_label = ttk.Label(self.ffmpeg_frame, text="FFmpeg not set.", wraplength=700, foreground="gray")
        self.ffmpeg_path_label.pack(side='left', padx=10)

        self.load_config()

    # Config
    def load_config(self):
        try:
            path = load_ffmpeg_path()
            if path:
                self.ffmpeg_path.set(path)
                self.ffmpeg_path_label.config(text=f"Path: ...{os.path.basename(path)}", foreground="green")
        except Exception:
            pass

    def save_config(self):
        save_ffmpeg_path(self.ffmpeg_path.get())

    def select_ffmpeg_path(self):
        path = filedialog.askopenfilename(
            title="Select ffmpeg.exe",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if path and "ffmpeg" in os.path.basename(path).lower():
            self.ffmpeg_path.set(path)
            self.ffmpeg_path_label.config(text=f"Path: ...{os.path.basename(path)}", foreground="green")
            self.save_config()
            messagebox.showinfo("Success", "FFmpeg path has been set and saved.")
        elif path:
            self.ffmpeg_path_label.config(text="Invalid file selected.", foreground="red")

    # Fetching
    def start_fetch_thread(self):
        self.reset_ui(is_fetching=True)
        self.status_label.config(text="Fetching video info...")
        threading.Thread(target=self.fetch_qualities, daemon=True).start()

    def fetch_qualities(self):
        url = self.url_entry.get()
        if not url:
            self.root.after(0, lambda: messagebox.showerror("Error", "Please enter a YouTube URL."))
            self.root.after(0, self.reset_ui)
            return
        try:
            video_info = fetch_video_info(url)
            self.yt_title = video_info.get('title', 'N/A')
            include_video_only = self.include_high_quality.get()
            self.yt_streams, self.stream_options = parse_streams(video_info, include_video_only)

            if not self.stream_options:
                msg = "No downloadable video streams were found."
                if not include_video_only:
                    msg += "\n\nTry checking the 'Include High-Quality' box for more options."
                self.root.after(0, lambda: messagebox.showwarning("No Streams", msg))
                self.root.after(0, self.reset_ui)
                return

            self.root.after(0, self.update_quality_menu)
        except FileNotFoundError:
            self.root.after(0, lambda: messagebox.showerror("Error", "yt-dlp not found.\nPlease install it with 'pip install yt-dlp'"))
            self.root.after(0, self.reset_ui)
        except Exception as e:
            import subprocess
            if isinstance(e, subprocess.CalledProcessError):
                error_message = (e.stderr or '').strip().split('\n')[-1]
                self.root.after(0, lambda: messagebox.showerror("Error", f"yt-dlp failed:\n{error_message}"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred: {e}"))
            self.root.after(0, self.reset_ui)

    def update_quality_menu(self):
        menu = self.quality_menu['menu']
        menu.delete(0, 'end')
        for option in self.stream_options:
            menu.add_command(label=option, command=lambda value=option: self.selected_quality.set(value))
        if self.stream_options:
            self.selected_quality.set(self.stream_options[0])
        self.quality_menu['state'] = 'normal'
        self.download_button['state'] = 'normal'
        self.fetch_button['state'] = 'normal'
        self.status_label.config(text=f"Fetched qualities for: {self.yt_title}")

    # Downloading
    def start_download_thread(self):
        try:
            selected_option = self.selected_quality.get()
            selected_index = self.stream_options.index(selected_option)
            stream = self.yt_streams[selected_index]

            if not stream['progressive']:
                try:
                    ensure_ffmpeg_available(self.ffmpeg_path.get() or 'ffmpeg')
                except Exception:
                    messagebox.showerror(
                        "FFmpeg Missing",
                        "Error: FFmpeg not found.\n\nPlease either set the path to ffmpeg.exe using the button below, or ensure it is correctly installed in your system's PATH."
                    )
                    return

            self.lock_ui_for_download()
            threading.Thread(target=self.download_video, daemon=True).start()
        except (ValueError, IndexError):
            messagebox.showerror("Error", "Please fetch and select a valid quality first.")

    def download_video(self):
        try:
            selected_option = self.selected_quality.get()
            selected_index = self.stream_options.index(selected_option)
            stream = self.yt_streams[selected_index]

            save_path = filedialog.askdirectory()
            if not save_path:
                self.root.after(0, self.reset_ui)
                self.status_label.config(text="Download cancelled.")
                return

            sanitized_title = re.sub(r'[\\/*?:"<>|]', "", self.yt_title)
            output_template = os.path.join(save_path, f"{sanitized_title}-{stream['res']}.mp4")

            command, is_hq_merge = build_download_command(
                stream=stream,
                url=self.url_entry.get(),
                output_template=output_template,
                ffmpeg_location=self.ffmpeg_path.get(),
            )

            print("--- Starting Download ---")
            print(f"DEBUG: Running yt-dlp command:\n{' '.join(command)}\n")

            def on_progress(pct: float, text: str):
                self.root.after(0, self.update_progress, pct, text)

            returncode, full_output = run_download(command, on_progress)
            print("--- Download Finished ---")

            if returncode == 0:
                self.root.after(0, lambda: messagebox.showinfo("Success", "Download complete!"))
            else:
                lower = full_output.lower()
                if "ffmpeg" in lower or "ffprobe" in lower:
                    error_msg = "Error: FFmpeg not found or failed.\n\nPlease use the 'Set FFmpeg Path' button to correctly point to your ffmpeg.exe file."
                else:
                    last_lines = "\n".join(full_output.strip().split('\n')[-5:])
                    error_msg = f"yt-dlp failed:\n\n...\n{last_lines}"
                self.root.after(0, lambda: messagebox.showerror("Download Error", error_msg))

            self.root.after(0, self.reset_ui)
        except Exception as e:
            print(f"--- PYTHON ERROR --- \n{e}\n--------------------")
            self.root.after(0, lambda: messagebox.showerror("Download Error", f"An error occurred: {e}"))
            self.root.after(0, self.reset_ui)

    # UI helpers
    def update_progress(self, percentage, status_text):
        self.progress_bar['value'] = percentage
        self.status_label.config(text=status_text.replace('[download]', '').strip())

    def lock_ui_for_download(self):
        self.fetch_button['state'] = 'disabled'
        self.download_button['state'] = 'disabled'
        self.quality_menu['state'] = 'disabled'
        self.hq_check['state'] = 'disabled'

    def reset_ui(self, is_fetching: bool = False):
        self.fetch_button['state'] = 'disabled' if is_fetching else 'normal'
        self.hq_check['state'] = 'disabled' if is_fetching else 'normal'
        self.download_button['state'] = 'disabled'
        self.quality_menu['state'] = 'disabled'
        if not is_fetching:
            self.selected_quality.set("No qualities fetched")
            self.status_label.config(text="")
        self.progress_bar['value'] = 0
