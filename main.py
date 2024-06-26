import tkinter as tk
from tkinter import font as tkfont, ttk
from backend import AudioProcessor
import threading

class TranscriptionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Meeting Guru")
        self.audio_processor = AudioProcessor()

        self.is_recording = False

        # Custom fonts
        self.header_font = tkfont.Font(family="Helvetica", size=14, weight="bold")
        self.normal_font = tkfont.Font(family="Helvetica", size=12)
        self.highlight_font = tkfont.Font(family="Helvetica", size=12, weight="bold", slant="italic")

        # Style for frames
        frame_style = {
            "bd": 2,
            "relief": tk.GROOVE,
            "bg": "#f7f7f7"
        }

        # Style for text areas
        text_area_style = {
            "bg": "#f0f0f0",
            "wrap": tk.WORD,
            "relief": tk.FLAT,
            "bd": 0
        }

        # Adding background image
        #self.bg_img = tk.PhotoImage(file="background.png")
        #self.bg_label = tk.Label(root, image=self.bg_img)
        #self.bg_label.place(relwidth=1, relheight=1)

        # Create text button instead of image button
        self.start_stop_button = tk.Button(
            root, text="Start", command=self.toggle_recording, 
            font=self.normal_font, bg="#4CAF50", fg="white", 
            activebackground="#45a049", activeforeground="white",
            padx=20, pady=10
        )
        self.start_stop_button.grid(row=0, column=0, columnspan=2, pady=20, padx=20, sticky="ew")

        self.current_transcription_frame = tk.LabelFrame(root, text="Current Transcription", font=self.header_font, **frame_style)
        self.current_transcription_frame.grid(row=1, column=0, padx=30, pady=10, sticky="nsew")
        self.current_transcription_text = tk.Text(self.current_transcription_frame, height=5, width=50, font=self.highlight_font, **text_area_style)
        self.current_transcription_text.pack(padx=10, pady=10)

        self.current_translation_frame = tk.LabelFrame(root, text="Current Translation", font=self.header_font, **frame_style)
        self.current_translation_frame.grid(row=1, column=1, padx=30, pady=10, sticky="nsew")
        self.current_translation_text = tk.Text(self.current_translation_frame, height=5, width=50, font=self.highlight_font, **text_area_style)
        self.current_translation_text.pack(padx=10, pady=10)

        self.comments_frame = tk.LabelFrame(root, text="Latest Insightful Comment", font=self.header_font, **frame_style)
        self.comments_frame.grid(row=2, column=0, columnspan=2, padx=30, pady=10, sticky="nsew")
        self.comments_text = tk.Text(self.comments_frame, height=5, width=100, font=self.normal_font, **text_area_style)
        self.comments_text.pack(padx=10, pady=10)

        self.full_transcription_frame = tk.LabelFrame(root, text="Full Auto-scrolling Transcription", font=self.header_font, **frame_style)
        self.full_transcription_frame.grid(row=3, column=0, padx=30, pady=10, sticky="nsew")
        self.full_transcription_text = tk.Text(self.full_transcription_frame, height=10, width=50, font=self.normal_font, **text_area_style)
        self.full_transcription_text.pack(padx=10, pady=10)

        self.full_translation_frame = tk.LabelFrame(root, text="Full Auto-scrolling Translation", font=self.header_font, **frame_style)
        self.full_translation_frame.grid(row=3, column=1, padx=30, pady=10, sticky="nsew")
        self.full_translation_text = tk.Text(self.full_translation_frame, height=10, width=50, font=self.normal_font, **text_area_style)
        self.full_translation_text.pack(padx=10, pady=10)

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_rowconfigure(3, weight=1)

    def toggle_recording(self):
        if self.is_recording:
            self.audio_processor.stop_recording()
            self.is_recording = False
            self.start_stop_button.config(text="Start", bg="#4CAF50", activebackground="#45a049")
        else:
            self.is_recording = True
            self.start_stop_button.config(text="Stop", bg="#f44336", activebackground="#d32f2f")
            threading.Thread(target=self.audio_processor.main_loop, args=(self.update_full_transcription, self.update_current_transcription, self.update_comments, self.update_full_translation, self.update_current_translation)).start()

    def update_full_transcription(self, transcription):
        self.full_transcription_text.delete("1.0", tk.END)
        self.full_transcription_text.insert(tk.END, transcription)
        self.full_transcription_text.see(tk.END)  # Auto-scroll to the end

    def update_current_transcription(self, transcription):
        self.current_transcription_text.delete("1.0", tk.END)
        self.current_transcription_text.insert(tk.END, transcription)

    def update_full_translation(self, translation):
        self.full_translation_text.delete("1.0", tk.END)
        self.full_translation_text.insert(tk.END, translation)
        self.full_translation_text.see(tk.END)  # Auto-scroll to the end

    def update_current_translation(self, translation):
        self.current_translation_text.delete("1.0", tk.END)
        self.current_translation_text.insert(tk.END, translation)

    def update_comments(self, comments):
        self.comments_text.delete("1.0", tk.END)
        self.comments_text.insert(tk.END, comments)
        self.comments_text.see(tk.END)  # Auto-scroll to the end

if __name__ == "__main__":
    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()
