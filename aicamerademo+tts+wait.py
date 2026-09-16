import tkinter as tk 
from tkinter import ttk
from ttkbootstrap import Style
from PIL import Image, ImageTk
import cv2
import base64
import requests
import threading
import tempfile
import time
import pygame
from gtts import gTTS

# Gemini API Key
API_KEY = "INPUT-YOUR-API-KEY"

# Gemini 3.5 Flash
#GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={API_KEY}"

# Gemini 3.8 Flash
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={API_KEY}"

class AICameraAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Camera Analyzer")
        self.root.geometry("1180x720")
        self.root.resizable(False, False)  # Disable maximize window
        self.style = Style("darkly")
        self.cap = None
        self.auto_mode = False

        self.build_ui()

    def build_ui(self):
        container = ttk.Frame(self.root, padding=10)
        container.pack(fill="both", expand=True)

        self.left_panel = ttk.Frame(container)
        self.left_panel.pack(side="left", padx=10, pady=10)

        self.right_panel = ttk.Frame(container)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Camera Display
        self.video_label = ttk.Label(
            self.left_panel,
            text="Camera is not active\nClick the camera button to start",
            anchor="center",
            bootstyle="inverse-secondary"
        )
        self.video_label.pack(pady=(10, 5))

        self.status_label = ttk.Label(self.left_panel, text="● Camera Inactive", bootstyle="danger")
        self.status_label.pack()

        button_frame = ttk.Frame(self.left_panel)
        button_frame.pack(pady=10)

        self.start_button = tk.Button(
            button_frame,
            text="📷 Start Camera",
            font=("Segoe UI", 11, "bold"),
            bg="#1f9d55",
            fg="white",
            activebackground="#38d39f",
            activeforeground="white",
            relief="solid",
            bd=2,
            padx=15,
            pady=8,
            command=self.start_camera,
            cursor="hand2"
        )
        self.start_button.pack(side="left", padx=5)

        self.analyze_button = tk.Button(
            button_frame,
            text="⚡ Analyze",
            font=("Segoe UI", 11, "bold"),
            bg="#343a40",
            fg="white",
            activebackground="#495057",
            activeforeground="white",
            relief="solid",
            bd=2,
            padx=15,
            pady=8,
            command=self.capture_and_analyze,
            cursor="hand2"
        )
        self.analyze_button.pack(side="left", padx=5)

        # Prompt & Response
        ttk.Label(self.right_panel, text="Instruction:", bootstyle="info").pack(anchor="w")
        self.prompt_text = tk.Text(self.right_panel, height=4, font=("Segoe UI", 14))
        self.prompt_text.insert("1.0", "Apa yang kamu lihat sekarang?")
        self.prompt_text.pack(fill="x", pady=(0, 10))

        ttk.Label(self.right_panel, text="Response:", bootstyle="info").pack(anchor="w")
        self.response_text = tk.Text(
            self.right_panel,
            height=12,
            bg="#1e1e2f",
            fg="#00ffaa",
            insertbackground="white",
            font=("Consolas", 13)
        )
        self.response_text.insert("1.0", "Analysis results will appear here...")
        self.response_text.pack(fill="both", expand=True, pady=(0, 10))

        interval_frame = ttk.Frame(self.right_panel)
        interval_frame.pack(anchor="w", pady=5)

        ttk.Label(interval_frame, text="Interval between 2 requests:").pack(side="left")
        self.interval_spin = ttk.Spinbox(interval_frame, from_=1, to=60, width=5)
        self.interval_spin.set(5)
        self.interval_spin.pack(side="left", padx=5)

        self.auto_button = ttk.Button(interval_frame, text="Start Auto", bootstyle="success", command=self.toggle_auto)
        self.auto_button.pack(side="left", padx=5)

    def start_camera(self):
        if not self.cap:
            self.cap = cv2.VideoCapture(0)
            self.status_label.config(text="● Camera Active", bootstyle="success")
            self.update_frame()

    def update_frame(self):
        if self.cap:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                imgtk = ImageTk.PhotoImage(image=img.resize((800, 560)))  # Enlarged camera frame
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
        if self.cap:
            self.root.after(10, self.update_frame)

    def capture_and_analyze(self):
        prompt = self.prompt_text.get("1.0", "end").strip()
        if not hasattr(self, "current_frame"):
            self.response_text.insert("1.0", "No camera frame found.")
            return

        self.analyze_button.config(state="disabled")
        threading.Thread(target=self.analyze_image, args=(prompt,), daemon=True).start()

    def analyze_image(self, prompt):
        _, buffer = cv2.imencode('.jpg', self.current_frame)
        image_bytes = buffer.tobytes()
        base64_img = base64.b64encode(image_bytes).decode()

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "Short response. "+prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": base64_img
                            }
                        }
                    ]
                }
            ]
        }

        headers = {"Content-Type": "application/json"}
        try:
            res = requests.post(GEMINI_URL, headers=headers, json=payload)
            res.raise_for_status()
            result = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            result = f"[Error] {str(e)}"

        # Tampilkan hasil di UI
        self.response_text.delete("1.0", "end")
        self.response_text.insert("1.0", result)
        self.analyze_button.config(state="normal")

        # TTS pakai thread
        threading.Thread(target=self.play_tts_and_continue, args=(result,), daemon=True).start()

    def play_tts_and_continue(self, text):
        try:
            tts = gTTS(text=text, lang='id')
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_file = fp.name
                tts.save(temp_file)

            pygame.mixer.init()
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()

            # tunggu sampai selesai bicara
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

            pygame.mixer.music.stop()
            time.sleep(0.3)

        except Exception as e:
            print("TTS Error:", e)

        # lanjut auto loop
        if self.auto_mode:
            delay = int(self.interval_spin.get()) * 1000
            self.root.after(delay, self.run_auto_loop)

    def toggle_auto(self):
        self.auto_mode = not self.auto_mode
        if self.auto_mode:
            self.auto_button.config(text="Stop Auto", bootstyle="danger")
            self.run_auto_loop()
        else:
            self.auto_button.config(text="Start Auto", bootstyle="success")

    def run_auto_loop(self):
        if self.auto_mode:
            self.capture_and_analyze()

    def __del__(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()


if __name__ == "__main__":
    root = tk.Tk()
    app = AICameraAnalyzerApp(root)
    root.mainloop()
