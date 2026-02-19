import customtkinter as ctk
import subprocess
import sys
import os
import json

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_FILE = os.path.join(BASE_DIR, "main.py")
SAVE_FILE = os.path.join(BASE_DIR, "save.json")


def load_save():
    if not os.path.exists(SAVE_FILE):
        save_data = {"max_level": 1, "last_level": 1}
        with open(SAVE_FILE, "w") as f:
            json.dump(save_data, f)
        return save_data

    with open(SAVE_FILE, "r") as f:
        return json.load(f)


def start_level(level):
    subprocess.run([sys.executable, GAME_FILE, str(level)])


save_data = load_save()

app = ctk.CTk()
app.geometry("700x500")
app.title("Меню")

title = ctk.CTkLabel(
    app,
    text="FPS GAME",
    font=ctk.CTkFont(size=40, weight="bold")
)
title.pack(pady=30)


continue_btn = ctk.CTkButton(
    app,
    text="Продолжить",
    width=250,
    height=60,
    command=lambda: start_level(save_data["last_level"])
)
continue_btn.pack(pady=10)


for i in range(1, 6):
    state = "normal" if i <= save_data["max_level"] else "disabled"

    btn = ctk.CTkButton(
        app,
        text=f"Уровень {i}",
        width=250,
        height=60,
        state=state,
        command=lambda lvl=i: start_level(lvl)
    )
    btn.pack(pady=5)

app.mainloop()
