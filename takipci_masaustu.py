"""Instagram takipçi listesini işleyen masaüstü uygulaması."""

from __future__ import annotations

import csv
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import pystray
from PIL import Image, ImageDraw, ImageTk
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def guvenli_hata_metni(exc: Exception, en_fazla: int = 500) -> str:
    """Günlüklere kullanıcı klasörü ve uzun sürücü çıktıları yazılmasını önler."""
    text = str(exc).split("Stacktrace:", 1)[0].strip()
    user_profile = os.environ.get("USERPROFILE", "")
    if user_profile:
        text = text.replace(user_profile, "%USERPROFILE%")
    return (text or type(exc).__name__)[:en_fazla]


def uygulama_veri_klasoru() -> Path:
    executable_dir = Path(
        sys.executable if getattr(sys, "frozen", False) else __file__
    ).parent
    folder = (
        Path(os.environ.get("LOCALAPPDATA", str(executable_dir)))
        / "BurakHocaInstagramPaneli"
    )
    folder.mkdir(parents=True, exist_ok=True)
    return folder


class TakipciUygulamasi:
    VERSION = "3.4.0"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.browser: Chrome | None = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.running = False
        self.loading_session = False
        executable_dir = Path(
            sys.executable if getattr(sys, "frozen", False) else __file__
        ).parent
        preferred_data_dir = (
            Path(os.environ.get("LOCALAPPDATA", str(executable_dir)))
            / "BurakHocaInstagramPaneli"
        )
        try:
            preferred_data_dir.mkdir(parents=True, exist_ok=True)
            self.app_dir = preferred_data_dir
        except OSError:
            self.app_dir = executable_dir / "InstagramTakipciPaneli_Veriler"
            self.app_dir.mkdir(parents=True, exist_ok=True)
        self.session_path = self.app_dir / "takipci_oturum.json"
        self.history_path = self.app_dir / "islem_gecmisi.json"
        self.diagnostics_dir = self.app_dir / "tanilama"
        self.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        self.history: list[dict] = self.load_history()
        self.processed_users = {
            item["username"].casefold()
            for item in self.history
            if item.get("result") == "Takip edildi" and item.get("username")
        }
        self.tray_icon = None
        self.all_iids: list[str] = []

        root.title("Instagram Takipçi Uygulaması Burak ÖZKAN")
        try:
            resource_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
            root.iconbitmap(str(resource_dir / "burakhoca_instagram_icon.ico"))
        except (OSError, tk.TclError):
            pass
        root.geometry("1120x870")
        root.minsize(960, 740)
        root.configure(bg="#090b12")
        root.protocol("WM_DELETE_WINDOW", self.close)
        tam_ekrani_engelle(root)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#090b12")
        style.configure(
            "Title.TLabel",
            background="#151824",
            foreground="#f9fafb",
            font=("Segoe UI", 22, "bold"),
        )
        style.configure(
            "Text.TLabel",
            background="#090b12",
            foreground="#c7cad4",
            font=("Segoe UI", 10),
        )
        style.configure(
            "TButton",
            background="#252b3d",
            foreground="#f8fafc",
            font=("Segoe UI", 10, "bold"),
            padding=10,
            borderwidth=0,
        )
        style.map("TButton", background=[("active", "#343b52")])
        style.configure(
            "Accent.TButton",
            background="#e1306c",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padding=11,
            borderwidth=0,
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#f04b82"), ("disabled", "#71334c")],
        )
        style.configure(
            "Stop.TButton",
            background="#3b2b16",
            foreground="#fbbf24",
            font=("Segoe UI", 10, "bold"),
            padding=11,
            borderwidth=0,
        )
        style.map("Stop.TButton", background=[("active", "#59401d")])
        style.configure(
            "Resume.TButton",
            background="#173526",
            foreground="#4ade80",
            font=("Segoe UI", 10, "bold"),
            padding=11,
            borderwidth=0,
        )
        style.map(
            "Resume.TButton",
            background=[("active", "#205238"), ("disabled", "#1c2923")],
        )
        style.configure(
            "Tool.TButton",
            background="#242038",
            foreground="#ddd6fe",
            font=("Segoe UI", 9, "bold"),
            padding=8,
            borderwidth=0,
        )
        style.map("Tool.TButton", background=[("active", "#382f59")])
        style.configure(
            "Menu.TButton",
            background="#252b3d",
            foreground="#e5e7eb",
            font=("Segoe UI", 9, "bold"),
            padding=9,
            borderwidth=0,
        )
        style.map("Menu.TButton", background=[("active", "#374151")])
        style.configure(
            "Instagram.Horizontal.TProgressbar",
            troughcolor="#252b3d",
            background="#a855f7",
            lightcolor="#a855f7",
            darkcolor="#a855f7",
            borderwidth=0,
            thickness=9,
        )
        style.configure(
            "Treeview",
            background="#111521",
            fieldbackground="#111521",
            foreground="#e5e7eb",
            rowheight=31,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.map(
            "Treeview",
            background=[("selected", "#6d28d9")],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "Treeview.Heading",
            background="#202638",
            foreground="#f9fafb",
            font=("Segoe UI", 10, "bold"),
            padding=8,
            borderwidth=0,
        )

        frame = ttk.Frame(root, padding=24)
        frame.pack(fill="both", expand=True)
        header = tk.Frame(frame, bg="#151824", padx=20, pady=16)
        header.pack(fill="x", pady=(0, 16))
        logo = tk.Label(
            header,
            text="IG",
            bg="#833ab4",
            fg="white",
            font=("Segoe UI", 16, "bold"),
            width=3,
            height=1,
        )
        logo.pack(side="left", padx=(0, 14))
        header_text = tk.Frame(header, bg="#151824")
        header_text.pack(side="left", fill="x", expand=True)
        ttk.Label(
            header_text, text="Instagram Takipçi Paneli", style="Title.TLabel"
        ).pack(anchor="w")
        tk.Label(
            header_text,
            text="Takipçi listesini algıla • sıraya al • kontrollü şekilde işle",
            bg="#151824",
            fg="#9ca3af",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(3, 0))
        self.state_badge = tk.Label(
            header,
            text="● HAZIR",
            bg="#17251f",
            fg="#4ade80",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=6,
        )
        self.state_badge.pack(side="right")
        ttk.Button(
            header,
            text="←  Ana Menü",
            command=self.return_to_main_menu,
            style="Menu.TButton",
        ).pack(side="right", padx=(0, 10))

        promo = tk.Frame(
            frame,
            bg="#171324",
            highlightbackground="#3b275c",
            highlightthickness=1,
            padx=18,
            pady=12,
        )
        promo.pack(fill="x", pady=(0, 12))
        promo_logo = tk.Frame(promo, bg="#e1306c", width=46, height=46)
        promo_logo.pack(side="left", padx=(0, 14))
        promo_logo.pack_propagate(False)
        tk.Label(
            promo_logo,
            text="BH",
            bg="#e1306c",
            fg="white",
            font=("Segoe UI", 14, "bold"),
        ).pack(expand=True)
        promo_text = tk.Frame(promo, bg="#171324")
        promo_text.pack(side="left", fill="x", expand=True)
        tk.Label(
            promo_text,
            text="BURAK HOCA • Dijital Eğitim & Danışmanlık",
            bg="#171324",
            fg="#ffffff",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        tk.Label(
            promo_text,
            text="@burakhocafen   •   www.burakhoca.com   •   0552 219 87 87",
            bg="#171324",
            fg="#c4b5fd",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 0))

        def promo_button(text: str, url: str, bg: str) -> None:
            button = tk.Button(
                promo,
                text=text,
                command=lambda: webbrowser.open(url),
                bg=bg,
                fg="white",
                activebackground="#f04b82",
                activeforeground="white",
                relief="flat",
                bd=0,
                cursor="hand2",
                font=("Segoe UI", 9, "bold"),
                padx=13,
                pady=7,
            )
            button.pack(side="left", padx=4)

        promo_button("Instagram", "https://www.instagram.com/burakhocafen/", "#833ab4")
        promo_button("Web Sitesi", "https://www.burakhoca.com", "#2563eb")
        promo_button("WhatsApp", "https://wa.me/905522198787", "#16a34a")

        controls = tk.Frame(frame, bg="#151824", padx=18, pady=14)
        controls.pack(fill="x")
        tk.Label(
            controls,
            text="Kişi sayısı",
            bg="#151824",
            fg="#c7cad4",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        self.count_var = tk.IntVar(value=5)
        self.count = ttk.Spinbox(
            controls, from_=1, to=100000, width=6, textvariable=self.count_var
        )
        self.count.pack(side="left", padx=(10, 18))
        tk.Label(
            controls,
            text="İşlem aralığı",
            bg="#151824",
            fg="#c7cad4",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        self.interval_var = tk.IntVar(value=30)
        self.interval = ttk.Spinbox(
            controls, from_=10, to=600, width=6, textvariable=self.interval_var
        )
        self.interval.pack(side="left", padx=(10, 18))
        self.start_button = ttk.Button(
            controls,
            text="▶  Tarayıcıyı Aç ve Başlat",
            command=self.start,
            style="Accent.TButton",
        )
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(
            controls,
            text="Ⅱ  Duraklat",
            command=self.pause,
            state="disabled",
            style="Stop.TButton",
        )
        self.stop_button.pack(side="left", padx=8)
        self.resume_button = ttk.Button(
            controls,
            text="▶  Devam Et",
            command=self.resume,
            state="disabled",
            style="Resume.TButton",
        )
        self.resume_button.pack(side="left")

        tools = tk.Frame(frame, bg="#10131d", padx=14, pady=10)
        tools.pack(fill="x", pady=(8, 0))
        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            tools, text="Deneme modu (tıklama yapma)", variable=self.dry_run_var
        ).pack(side="left", padx=(0, 12))
        tk.Label(
            tools,
            text="Günlük limit",
            bg="#10131d",
            fg="#c7cad4",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        self.daily_limit_var = tk.IntVar(value=100000)
        ttk.Spinbox(
            tools, from_=1, to=100000, width=5, textvariable=self.daily_limit_var
        ).pack(side="left", padx=(8, 14))
        ttk.Button(
            tools, text="CSV Al", command=self.import_csv, style="Tool.TButton"
        ).pack(side="left", padx=3)
        ttk.Button(
            tools, text="CSV Ver", command=self.export_csv, style="Tool.TButton"
        ).pack(side="left", padx=3)
        ttk.Button(
            tools,
            text="Hataları Yeniden Dene",
            command=self.retry_failed,
            style="Tool.TButton",
        ).pack(
            side="left", padx=3
        )
        ttk.Button(
            tools,
            text="Tepsiye Küçült",
            command=self.hide_to_tray,
            style="Tool.TButton",
        ).pack(
            side="left", padx=3
        )
        self.theme_var = tk.StringVar(value="Instagram")
        theme_box = ttk.Combobox(
            tools,
            textvariable=self.theme_var,
            values=("Instagram", "Gece", "Açık"),
            width=10,
            state="readonly",
        )
        theme_box.pack(side="right")
        theme_box.bind("<<ComboboxSelected>>", self.change_theme)

        shutdown_card = tk.Frame(
            frame,
            bg="#151824",
            highlightbackground="#3b2b16",
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        shutdown_card.pack(fill="x", pady=(8, 0))
        tk.Label(
            shutdown_card,
            text="PC OTOMATİK KAPATMA",
            bg="#151824",
            fg="#fbbf24",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 14))
        self.shutdown_mode_var = tk.StringVar(value="Süre sonra")
        shutdown_mode = ttk.Combobox(
            shutdown_card,
            textvariable=self.shutdown_mode_var,
            values=("Süre sonra", "Belirli saatte"),
            width=15,
            state="readonly",
        )
        shutdown_mode.pack(side="left")
        shutdown_mode.bind("<<ComboboxSelected>>", self.update_shutdown_hint)
        self.shutdown_value_var = tk.StringVar(value="60")
        self.shutdown_value_entry = ttk.Entry(
            shutdown_card, textvariable=self.shutdown_value_var, width=10
        )
        self.shutdown_value_entry.pack(side="left", padx=(8, 5))
        self.shutdown_hint_var = tk.StringVar(value="dakika")
        tk.Label(
            shutdown_card,
            textvariable=self.shutdown_hint_var,
            bg="#151824",
            fg="#c7cad4",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 12))
        ttk.Button(
            shutdown_card,
            text="Kapatmayı Planla",
            command=self.schedule_shutdown,
            style="Stop.TButton",
        ).pack(side="left", padx=3)
        ttk.Button(
            shutdown_card,
            text="Planı İptal Et",
            command=self.cancel_shutdown,
            style="Tool.TButton",
        ).pack(side="left", padx=3)
        self.shutdown_status_var = tk.StringVar(value="Plan yok")
        tk.Label(
            shutdown_card,
            textvariable=self.shutdown_status_var,
            bg="#151824",
            fg="#9ca3af",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right")

        self.queued_var = tk.StringVar(value="0")
        self.completed_var = tk.StringVar(value="0")
        self.skipped_var = tk.StringVar(value="0")
        stats = tk.Frame(frame, bg="#090b12")
        stats.pack(fill="x", pady=(12, 0))

        def stat_card(title: str, variable: tk.StringVar, color: str) -> None:
            card = tk.Frame(
                stats,
                bg="#151824",
                highlightbackground="#252b3d",
                highlightthickness=1,
                padx=16,
                pady=10,
            )
            card.pack(side="left", fill="x", expand=True, padx=(0, 10))
            tk.Label(
                card,
                text=title.upper(),
                bg="#151824",
                fg="#8f96a8",
                font=("Segoe UI", 8, "bold"),
            ).pack(anchor="w")
            tk.Label(
                card,
                textvariable=variable,
                bg="#151824",
                fg=color,
                font=("Segoe UI", 18, "bold"),
            ).pack(anchor="w", pady=(2, 0))

        stat_card("Listeye alınan", self.queued_var, "#c4b5fd")
        stat_card("Takip edilen", self.completed_var, "#4ade80")
        stat_card("Atlanan", self.skipped_var, "#fb7185")
        step_card = tk.Frame(
            stats,
            bg="#151824",
            highlightbackground="#252b3d",
            highlightthickness=1,
            padx=16,
            pady=10,
        )
        step_card.pack(side="left", fill="x", expand=True)
        tk.Label(
            step_card,
            text="AKIŞ",
            bg="#151824",
            fg="#8f96a8",
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w")
        tk.Label(
            step_card,
            text="Listele  →  Bekle  →  Takip Et",
            bg="#151824",
            fg="#f9a8d4",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(6, 4))

        self.status_var = tk.StringVar(value="Hazır")
        status_card = tk.Frame(frame, bg="#151824", padx=18, pady=12)
        status_card.pack(fill="x", pady=(12, 12))
        tk.Label(
            status_card,
            textvariable=self.status_var,
            bg="#151824",
            fg="#e9d5ff",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        self.progress = ttk.Progressbar(
            status_card, mode="determinate", style="Instagram.Horizontal.TProgressbar"
        )
        self.progress.pack(fill="x")

        content = ttk.Panedwindow(frame, orient="horizontal")
        content.pack(fill="both", expand=True)

        list_frame = ttk.Frame(content, padding=(0, 0, 8, 0))
        log_frame = ttk.Frame(content, padding=(8, 0, 0, 0))
        content.add(list_frame, weight=3)
        content.add(log_frame, weight=2)

        ttk.Label(list_frame, text="İşlem Listesi", style="Text.TLabel").pack(
            anchor="w", pady=(0, 6)
        )
        list_tools = tk.Frame(list_frame, bg="#090b12")
        list_tools.pack(fill="x", pady=(0, 6))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(list_tools, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.bind("<KeyRelease>", self.apply_filter)
        self.filter_var = tk.StringVar(value="Tümü")
        filter_box = ttk.Combobox(
            list_tools,
            textvariable=self.filter_var,
            values=("Tümü", "Bekliyor", "Takip edildi", "Atlandı", "Deneme"),
            width=12,
            state="readonly",
        )
        filter_box.pack(side="left", padx=(6, 0))
        filter_box.bind("<<ComboboxSelected>>", self.apply_filter)
        ttk.Button(
            list_tools,
            text="Listeyi Temizle",
            command=self.clear_list_confirm,
            style="Tool.TButton",
        ).pack(side="left", padx=(6, 0))
        self.queue_tree = ttk.Treeview(
            list_frame,
            columns=("no", "username", "status"),
            show="headings",
            selectmode="browse",
        )
        self.queue_tree.heading("no", text="#")
        self.queue_tree.heading("username", text="Kullanıcı")
        self.queue_tree.heading("status", text="Durum")
        self.queue_tree.column("no", width=44, anchor="center", stretch=False)
        self.queue_tree.column("username", width=210)
        self.queue_tree.column("status", width=120, anchor="center")
        self.queue_tree.pack(fill="both", expand=True)
        self.queue_tree.tag_configure("waiting", foreground="#fbbf24")
        self.queue_tree.tag_configure("done", foreground="#4ade80")
        self.queue_tree.tag_configure("skipped", foreground="#fb7185")
        self.queue_tree.tag_configure("dry", foreground="#60a5fa")
        self.queue_tree.bind("<Double-1>", self.open_selected_profile)
        self.queue_tree.bind("<Button-3>", self.show_queue_context_menu)
        self.queue_tree.bind("<Delete>", lambda _event: self.delete_selected())
        self.queue_context_menu = tk.Menu(
            self.root,
            tearoff=False,
            bg="#1f2433",
            fg="#f8fafc",
            activebackground="#e1306c",
            activeforeground="#ffffff",
        )
        self.queue_context_menu.add_command(
            label="Seçili kullanıcıyı sil", command=self.delete_selected
        )
        self.queue_context_menu.add_separator()
        self.queue_context_menu.add_command(
            label="Tüm listeyi temizle", command=self.clear_list_confirm
        )

        ttk.Label(log_frame, text="Canlı Günlük", style="Text.TLabel").pack(
            anchor="w", pady=(0, 6)
        )
        self.log_box = tk.Text(
            log_frame,
            height=12,
            bg="#111521",
            fg="#c4b5fd",
            insertbackground="white",
            relief="flat",
            font=("Consolas", 10),
            state="disabled",
        )
        self.log_box.pack(fill="both", expand=True)
        self.log("Uygulama hazır.")
        self.load_session()

        footer = tk.Frame(frame, bg="#090b12", pady=8)
        footer.pack(fill="x")
        tk.Label(
            footer,
            text="🔒 Oturum ve işlem listesi otomatik kaydedilir",
            bg="#090b12",
            fg="#6b7280",
            font=("Segoe UI", 8),
        ).pack(side="left")
        tk.Label(
            footer,
            text=f"Instagram Takipçi Paneli v{self.VERSION} • Yerel masaüstü uygulaması",
            bg="#090b12",
            fg="#4b5563",
            font=("Segoe UI", 8),
        ).pack(side="right", padx=(8, 0))
        ttk.Button(footer, text="Sürümü Kontrol Et", command=self.check_version).pack(
            side="right"
        )

    def ui(self, callback, *args, **kwargs) -> None:
        # Tkinter yalnızca ana UI iş parçacığından güncellenebilir. Lambda,
        # configure(value=...) gibi isimli parametreleri de güvenle taşır.
        self.root.after(0, lambda: callback(*args, **kwargs))

    def log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def set_status(self, text: str) -> None:
        self.status_var.set(text)
        normalized = text.casefold()
        if "tamamlandı" in normalized:
            self.state_badge.configure(
                text="● TAMAMLANDI", bg="#17251f", fg="#4ade80"
            )
        elif "hata" in normalized or "açılmadı" in normalized:
            self.state_badge.configure(text="● HATA", bg="#351c26", fg="#fb7185")
        elif "durdur" in normalized or "duraklat" in normalized:
            self.state_badge.configure(text="● DURUYOR", bg="#322816", fg="#fbbf24")
        else:
            self.state_badge.configure(
                text="● ÇALIŞIYOR", bg="#241b3a", fg="#c4b5fd"
            )
        self.log(text)

    def clear_queue(self) -> None:
        for item in list(self.all_iids):
            if self.queue_tree.exists(item):
                self.queue_tree.delete(item)
        self.all_iids.clear()
        self.queued_var.set("0")
        self.completed_var.set("0")
        self.skipped_var.set("0")
        self.save_session()

    def clear_list_confirm(self) -> None:
        if not self.all_iids:
            return
        if not messagebox.askyesno(
            "Listeyi temizle",
            "Listedeki bütün kullanıcılar silinsin mi?\n"
            "İşlem geçmişi silinmeyecek.",
        ):
            return
        self.clear_queue()
        self.progress.configure(value=0, maximum=1)
        self.resume_button.configure(state="disabled")
        self.log("İşlem listesi temizlendi.")

    def show_queue_context_menu(self, event) -> None:
        item = self.queue_tree.identify_row(event.y)
        if not item:
            return
        self.queue_tree.selection_set(item)
        self.queue_tree.focus(item)
        try:
            self.queue_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.queue_context_menu.grab_release()

    def delete_selected(self) -> None:
        selected = self.queue_tree.selection()
        if not selected:
            return
        for item in selected:
            if self.queue_tree.exists(item):
                self.queue_tree.delete(item)
            if item in self.all_iids:
                self.all_iids.remove(item)

        for number, item in enumerate(self.all_iids, start=1):
            if self.queue_tree.exists(item):
                values = list(self.queue_tree.item(item, "values"))
                values[0] = number
                self.queue_tree.item(item, values=values)

        done = sum(
            1
            for item in self.all_iids
            if self.queue_tree.exists(item)
            and self.queue_tree.item(item, "values")[2] == "Takip edildi"
        )
        skipped = sum(
            1
            for item in self.all_iids
            if self.queue_tree.exists(item)
            and self.queue_tree.item(item, "values")[2] == "Atlandı"
        )
        self.queued_var.set(str(len(self.all_iids)))
        self.completed_var.set(str(done))
        self.skipped_var.set(str(skipped))
        self.progress.configure(
            maximum=max(len(self.all_iids), 1), value=min(done, len(self.all_iids))
        )
        has_pending = any(
            self.queue_tree.exists(item)
            and self.queue_tree.item(item, "values")[2] == "Bekliyor"
            for item in self.all_iids
        )
        if not self.running:
            self.resume_button.configure(state="normal" if has_pending else "disabled")
        self.save_session()
        self.log("Seçili kullanıcı listeden silindi.")

    def queue_add(self, profile: str) -> None:
        username = profile.rstrip("/").rsplit("/", 1)[-1]
        if not username or self.queue_tree.exists(username):
            return
        number = len(self.queue_tree.get_children()) + 1
        self.queue_tree.insert(
            "",
            "end",
            iid=username,
            values=(number, f"@{username}", "Bekliyor"),
            tags=("waiting",),
        )
        self.all_iids.append(username)
        self.queued_var.set(str(len(self.queue_tree.get_children())))
        self.save_session()

    def queue_status(self, profile: str, status: str) -> None:
        username = profile.rstrip("/").rsplit("/", 1)[-1]
        if self.queue_tree.exists(username):
            values = list(self.queue_tree.item(username, "values"))
            values[2] = status
            tag = (
                "done"
                if status == "Takip edildi"
                else "dry"
                if status == "Deneme"
                else "skipped"
            )
            self.queue_tree.item(username, values=values, tags=(tag,))
            self.queue_tree.see(username)
            done = sum(
                1
                for item in self.queue_tree.get_children()
                if self.queue_tree.item(item, "values")[2] == "Takip edildi"
            )
            skipped = sum(
                1
                for item in self.queue_tree.get_children()
                if self.queue_tree.item(item, "values")[2] == "Atlandı"
            )
            self.completed_var.set(str(done))
            self.skipped_var.set(str(skipped))
            if not self.loading_session and status != "Bekliyor":
                self.add_history(profile, status)
            self.save_session()

    def save_session(self) -> None:
        if self.loading_session:
            return
        try:
            items = []
            for item in self.queue_tree.get_children():
                values = self.queue_tree.item(item, "values")
                items.append(
                    {
                        "profile": f"https://www.instagram.com/{item}/",
                        "status": values[2],
                    }
                )
            payload = {
                "interval": int(self.interval_var.get()),
                "items": items,
            }
            self.session_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except (OSError, ValueError, tk.TclError):
            pass

    def load_session(self) -> None:
        if not self.session_path.exists():
            return
        try:
            payload = json.loads(self.session_path.read_text(encoding="utf-8"))
            self.loading_session = True
            self.interval_var.set(int(payload.get("interval", 30)))
            for item in payload.get("items", []):
                profile = item.get("profile", "")
                status = item.get("status", "Bekliyor")
                if not profile:
                    continue
                self.queue_add(profile)
                if status != "Bekliyor":
                    self.queue_status(profile, status)
            pending = any(
                self.queue_tree.item(item, "values")[2] == "Bekliyor"
                for item in self.queue_tree.get_children()
            )
            if pending:
                self.resume_button.configure(state="normal")
                self.log("Önceki oturum yüklendi; kaldığı yerden devam edilebilir.")
            total = len(self.queue_tree.get_children())
            self.progress.configure(
                maximum=max(total, 1), value=int(self.completed_var.get())
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
        finally:
            self.loading_session = False

    def load_history(self) -> list[dict]:
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def add_history(self, profile: str, result: str) -> None:
        username = profile.rstrip("/").rsplit("/", 1)[-1]
        self.history.append(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "username": username,
                "profile": profile,
                "result": result,
            }
        )
        if result == "Takip edildi":
            self.processed_users.add(username.casefold())
        try:
            self.history_path.write_text(
                json.dumps(self.history, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def import_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Kullanıcı listesini seç",
            filetypes=(("CSV dosyası", "*.csv"), ("Tüm dosyalar", "*.*")),
        )
        if not path:
            return
        added = 0
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as source:
                for row in csv.reader(source):
                    if not row:
                        continue
                    username = row[0].strip().lstrip("@")
                    if not username or username.casefold() in {"kullanıcı", "username"}:
                        continue
                    profile = f"https://www.instagram.com/{username}/"
                    before = len(self.all_iids)
                    self.queue_add(profile)
                    added += len(self.all_iids) - before
            self.resume_button.configure(state="normal")
            self.log(f"CSV'den {added} kullanıcı eklendi.")
        except (OSError, csv.Error) as exc:
            messagebox.showerror("CSV hatası", str(exc))

    def export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Listeyi kaydet",
            defaultextension=".csv",
            filetypes=(("CSV dosyası", "*.csv"),),
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as target:
                writer = csv.writer(target)
                writer.writerow(("Kullanıcı", "Durum", "Profil"))
                for item in self.all_iids:
                    if not self.queue_tree.exists(item):
                        continue
                    values = self.queue_tree.item(item, "values")
                    writer.writerow((values[1], values[2], f"https://www.instagram.com/{item}/"))
            self.log(f"Liste CSV olarak kaydedildi: {path}")
        except OSError as exc:
            messagebox.showerror("CSV hatası", str(exc))

    def retry_failed(self) -> None:
        changed = 0
        for item in self.all_iids:
            if not self.queue_tree.exists(item):
                continue
            values = list(self.queue_tree.item(item, "values"))
            if values[2] == "Atlandı":
                values[2] = "Bekliyor"
                self.queue_tree.item(item, values=values, tags=("waiting",))
                changed += 1
        if changed:
            self.resume_button.configure(state="normal")
            self.save_session()
        self.log(f"{changed} başarısız işlem tekrar kuyruğuna alındı.")

    def apply_filter(self, _event=None) -> None:
        search = self.search_var.get().strip().casefold()
        selected = self.filter_var.get()
        for item in self.all_iids:
            if not self.queue_tree.exists(item):
                continue
            values = self.queue_tree.item(item, "values")
            visible = (not search or search in str(values[1]).casefold()) and (
                selected == "Tümü" or values[2] == selected
            )
            if visible:
                self.queue_tree.reattach(item, "", "end")
            else:
                self.queue_tree.detach(item)

    def open_selected_profile(self, _event=None) -> None:
        selected = self.queue_tree.selection()
        if not selected:
            return
        profile = f"https://www.instagram.com/{selected[0]}/"
        if self.browser is not None:
            threading.Thread(target=self.browser.get, args=(profile,), daemon=True).start()
        else:
            webbrowser.open(profile)

    def change_theme(self, _event=None) -> None:
        themes = {
            "Instagram": {
                "bg": "#090b12",
                "surface": "#151824",
                "surface2": "#111521",
                "fg": "#f8fafc",
                "muted": "#c7cad4",
                "accent": "#e1306c",
                "border": "#252b3d",
            },
            "Gece": {
                "bg": "#05070a",
                "surface": "#10151c",
                "surface2": "#090d13",
                "fg": "#f8fafc",
                "muted": "#b8c1cc",
                "accent": "#38bdf8",
                "border": "#243141",
            },
            "Açık": {
                "bg": "#e9edf3",
                "surface": "#ffffff",
                "surface2": "#f6f8fb",
                "fg": "#111827",
                "muted": "#374151",
                "accent": "#7c3aed",
                "border": "#cbd5e1",
            },
        }
        palette = themes[self.theme_var.get()]
        bg = palette["bg"]
        surface = palette["surface"]
        surface2 = palette["surface2"]
        fg = palette["fg"]
        muted = palette["muted"]
        accent = palette["accent"]
        border = palette["border"]

        self.root.configure(bg=bg)
        style = ttk.Style()
        style.configure("TFrame", background=bg)
        style.configure("Title.TLabel", background=surface, foreground=fg)
        style.configure("Text.TLabel", background=bg, foreground=muted)
        style.configure("TCheckbutton", background=surface, foreground=fg)
        style.map(
            "TCheckbutton",
            background=[("active", surface)],
            foreground=[("active", fg)],
        )
        style.configure("TEntry", fieldbackground=surface2, foreground=fg)
        style.configure("TSpinbox", fieldbackground=surface2, foreground=fg)
        style.configure(
            "TCombobox",
            fieldbackground=surface2,
            background=surface2,
            foreground=fg,
            arrowcolor=fg,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", surface2)],
            foreground=[("readonly", fg)],
            selectbackground=[("readonly", surface2)],
            selectforeground=[("readonly", fg)],
        )
        style.configure(
            "Treeview",
            background=surface2,
            fieldbackground=surface2,
            foreground=fg,
            bordercolor=border,
        )
        style.map(
            "Treeview",
            background=[("selected", accent)],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "Treeview.Heading",
            background="#dde3ec" if self.theme_var.get() == "Açık" else "#202638",
            foreground=fg,
        )
        style.configure(
            "Instagram.Horizontal.TProgressbar",
            troughcolor="#d6dce5" if self.theme_var.get() == "Açık" else "#252b3d",
            background=accent,
            lightcolor=accent,
            darkcolor=accent,
        )
        style.configure("Accent.TButton", background=accent, foreground="#ffffff")
        style.configure(
            "Tool.TButton",
            background="#e5e7eb" if self.theme_var.get() == "Açık" else "#242038",
            foreground="#111827" if self.theme_var.get() == "Açık" else "#ddd6fe",
        )

        def recolor(widget) -> None:
            try:
                if isinstance(widget, tk.Frame):
                    widget.configure(
                        bg=surface,
                        highlightbackground=border,
                    )
                elif isinstance(widget, tk.Label):
                    widget.configure(bg=surface, fg=fg)
                elif isinstance(widget, tk.Text):
                    widget.configure(
                        bg=surface2,
                        fg=fg,
                        insertbackground=fg,
                        selectbackground=accent,
                        selectforeground="#ffffff",
                    )
                elif isinstance(widget, tk.Menu):
                    widget.configure(
                        bg=surface,
                        fg=fg,
                        activebackground=accent,
                        activeforeground="#ffffff",
                    )
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                recolor(child)

        recolor(self.root)
        self.root.configure(bg=bg)

        self.queue_tree.tag_configure(
            "waiting",
            foreground="#92400e" if self.theme_var.get() == "Açık" else "#fbbf24",
        )
        self.queue_tree.tag_configure(
            "done",
            foreground="#047857" if self.theme_var.get() == "Açık" else "#4ade80",
        )
        self.queue_tree.tag_configure(
            "skipped",
            foreground="#be123c" if self.theme_var.get() == "Açık" else "#fb7185",
        )
        self.queue_tree.tag_configure(
            "dry",
            foreground="#1d4ed8" if self.theme_var.get() == "Açık" else "#60a5fa",
        )
        self.log(f"{self.theme_var.get()} teması seçildi.")

    def notify(self, title: str, message: str) -> None:
        try:
            if self.tray_icon is not None:
                self.tray_icon.notify(message, title)
            else:
                self.root.bell()
        except Exception:
            pass

    def hide_to_tray(self) -> None:
        if self.tray_icon is not None:
            self.root.withdraw()
            return
        image = Image.new("RGB", (64, 64), "#833ab4")
        draw = ImageDraw.Draw(image)
        draw.ellipse((15, 15, 49, 49), outline="white", width=5)
        draw.ellipse((42, 12, 49, 19), fill="white")

        def show_window(_icon=None, _item=None):
            self.root.after(0, self.root.deiconify)

        def quit_app(icon=None, _item=None):
            if icon:
                icon.stop()
            self.root.after(0, self.close)

        self.tray_icon = pystray.Icon(
            "InstagramTakipciPaneli",
            image,
            "Instagram Takipçi Paneli",
            menu=pystray.Menu(
                pystray.MenuItem("Göster", show_window, default=True),
                pystray.MenuItem("Çıkış", quit_app),
            ),
        )
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        self.root.withdraw()

    def save_diagnostics(self, exc: Exception) -> None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            (self.diagnostics_dir / f"hata_{stamp}.txt").write_text(
                f"{type(exc).__name__}: {guvenli_hata_metni(exc)}",
                encoding="utf-8",
            )
        except Exception:
            pass

    def check_version(self) -> None:
        version_file = self.app_dir / "latest_version.json"
        try:
            latest = json.loads(version_file.read_text(encoding="utf-8")).get(
                "version", self.VERSION
            )
        except (OSError, json.JSONDecodeError):
            latest = self.VERSION
        if latest == self.VERSION:
            messagebox.showinfo(
                "Sürüm kontrolü", f"En güncel yerel sürüm kullanılıyor: v{self.VERSION}"
            )
        else:
            messagebox.showinfo(
                "Yeni sürüm",
                f"Kurulu: v{self.VERSION}\nKayıtlı son sürüm: v{latest}",
            )

    def update_shutdown_hint(self, _event=None) -> None:
        if self.shutdown_mode_var.get() == "Süre sonra":
            self.shutdown_hint_var.set("dakika (ör. 60)")
            self.shutdown_value_var.set("60")
        else:
            self.shutdown_hint_var.set("saat (ör. 23:30)")
            self.shutdown_value_var.set(
                (datetime.now() + timedelta(hours=1)).strftime("%H:%M")
            )

    def schedule_shutdown(self) -> None:
        value = self.shutdown_value_var.get().strip()
        now = datetime.now()
        try:
            if self.shutdown_mode_var.get() == "Süre sonra":
                minutes = int(value)
                if not 1 <= minutes <= 10080:
                    raise ValueError
                seconds = minutes * 60
                target = now + timedelta(seconds=seconds)
            else:
                target_time = datetime.strptime(value, "%H:%M").time()
                target = datetime.combine(now.date(), target_time)
                if target <= now + timedelta(seconds=30):
                    target += timedelta(days=1)
                seconds = max(60, int((target - now).total_seconds()))
        except ValueError:
            messagebox.showwarning(
                "Geçersiz kapatma zamanı",
                "Süre için 1-10080 dakika veya saat için HH:MM biçimi kullan.\n"
                "Örnek: 60 ya da 23:30",
            )
            return

        if not messagebox.askyesno(
            "PC kapatmayı planla",
            f"Bilgisayar {target.strftime('%d.%m.%Y %H:%M')} tarihinde kapatılsın mı?\n\n"
            "Kaydedilmemiş çalışmalarını kapatma zamanından önce kaydet.",
        ):
            return
        try:
            result = subprocess.run(
                ["shutdown.exe", "/s", "/t", str(seconds)],
                check=False,
                capture_output=True,
                text=True,
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            if result.returncode != 0:
                raise OSError(result.stderr.strip() or "Windows planlamayı reddetti.")
            self.shutdown_status_var.set(
                f"Planlandı: {target.strftime('%d.%m %H:%M')}"
            )
            self.log(
                f"PC kapatma planlandı: {target.strftime('%d.%m.%Y %H:%M')}."
            )
        except OSError as exc:
            messagebox.showerror("Kapatma planlanamadı", str(exc))

    def cancel_shutdown(self) -> None:
        try:
            result = subprocess.run(
                ["shutdown.exe", "/a"],
                check=False,
                capture_output=True,
                text=True,
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            if result.returncode != 0:
                self.shutdown_status_var.set("Aktif plan bulunamadı")
                self.log("İptal edilecek aktif PC kapatma planı bulunamadı.")
                return
            self.shutdown_status_var.set("Plan iptal edildi")
            self.log("PC otomatik kapatma planı iptal edildi.")
        except OSError as exc:
            messagebox.showerror("Kapatma iptal edilemedi", str(exc))

    def create_browser(self) -> Chrome:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        profile_dir = self.app_dir / "ChromeProfile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        return Chrome(options=options)

    def ensure_browser(self) -> Chrome:
        """Açık Chrome oturumunu yeniden kullan, kapanmışsa yenisini oluştur."""
        if self.browser is not None:
            try:
                _ = self.browser.current_url
                _ = self.browser.window_handles
                if self.browser.window_handles:
                    self.browser.switch_to.window(self.browser.window_handles[-1])
                    return self.browser
            except WebDriverException:
                try:
                    self.browser.quit()
                except WebDriverException:
                    pass
                self.browser = None
                time.sleep(1)
        self.browser = self.create_browser()
        return self.browser

    def wait_while_paused(self) -> bool:
        while self.pause_event.is_set() and not self.stop_event.is_set():
            time.sleep(0.25)
        return not self.stop_event.is_set()

    def start(self) -> None:
        if self.running:
            return
        try:
            wanted = int(self.count_var.get())
            interval = int(self.interval_var.get())
            daily_limit = int(self.daily_limit_var.get())
            if not 1 <= wanted <= 100000:
                raise ValueError
            if not 10 <= interval <= 600:
                raise ValueError
            if not 1 <= daily_limit <= 100000:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showwarning(
                "Geçersiz değer",
                "Kişi sayısı 1-100000, işlem aralığı 10-600 saniye olmalı.",
            )
            return
        today = datetime.now().date().isoformat()
        today_count = sum(
            1
            for item in self.history
            if item.get("result") == "Takip edildi"
            and str(item.get("timestamp", "")).startswith(today)
        )
        if not self.dry_run_var.get() and today_count + wanted > daily_limit:
            messagebox.showwarning(
                "Günlük limit",
                f"Bugün {today_count} işlem yapılmış. Günlük {daily_limit} "
                "limitini aşmadan kişi sayısını azalt.",
            )
            return

        self.running = True
        self.stop_event.clear()
        self.pause_event.clear()
        self.clear_queue()
        self.progress.configure(maximum=wanted, value=0)
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.resume_button.configure(state="disabled")
        threading.Thread(
            target=self.worker, args=(wanted, interval), daemon=True
        ).start()

    def wait_interval(self, seconds: int, completed: int, wanted: int) -> bool:
        for remaining in range(seconds, 0, -1):
            if self.stop_event.is_set():
                return False
            if not self.wait_while_paused():
                return False
            self.ui(
                self.status_var.set,
                f"{completed}/{wanted} tamamlandı — sonraki işlem: {remaining} sn",
            )
            if self.stop_event.wait(1):
                return False
        return True

    def worker(self, wanted: int, interval: int) -> None:
        try:
            self.ui(self.set_status, "Chrome açılıyor...")
            self.browser = self.ensure_browser()
            self.browser.get("https://www.instagram.com/")
            self.ui(
                self.set_status,
                "Instagram'a giriş yap ve hedef profilin takipçiler listesini aç.",
            )

            dialog = WebDriverWait(self.browser, 600).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div[role='dialog']"))
            )
            self.ui(self.set_status, "Takipçi listesi bulundu; kullanıcılar aktarılıyor.")
            self.ui(self.log, f"İşlem aralığı: {interval} saniye.")
            queue: list[str] = []
            seen: set[str] = set()
            empty_rounds = 0

            # 1. AŞAMA: Açılan takipçi penceresinden kullanıcıları tabloya aktar.
            while (
                len(queue) < wanted
                and empty_rounds < 8
                and not self.stop_event.is_set()
                and self.wait_while_paused()
            ):
                before = len(queue)
                try:
                    dialog = self.browser.find_element(
                        By.CSS_SELECTOR, "div[role='dialog']"
                    )
                except NoSuchElementException:
                    self.ui(
                        self.log,
                        f"Takipçi penceresi kapatıldı; mevcut {len(queue)} "
                        "kullanıcıyla devam ediliyor.",
                    )
                    break
                for link in dialog.find_elements(By.CSS_SELECTOR, "a[href]"):
                    try:
                        profile = link.get_attribute("href")
                        if not profile:
                            continue
                        parsed = urlparse(profile)
                        parts = [part for part in parsed.path.split("/") if part]
                        if len(parts) != 1:
                            continue
                        username = parts[0].casefold()
                        if username in {
                            "accounts",
                            "explore",
                            "reels",
                            "direct",
                            self.browser.current_url.rstrip("/").rsplit("/", 1)[-1].casefold(),
                        }:
                            continue
                        if username in self.processed_users:
                            continue
                        normalized = f"https://www.instagram.com/{parts[0]}/"
                        if normalized in seen:
                            continue
                        # Yalnızca yanında takip düğmesi olan satırları listele.
                        row = link.find_element(
                            By.XPATH, "./ancestor::div[.//button][1]"
                        )
                        labels = {
                            button.text.strip().casefold()
                            for button in row.find_elements(By.TAG_NAME, "button")
                        }
                        if not labels.intersection({"takip et", "follow"}):
                            continue
                        seen.add(normalized)
                        queue.append(normalized)
                        self.ui(self.queue_add, normalized)
                        self.ui(
                            self.status_var.set,
                            f"Liste aktarılıyor: {len(queue)}/{wanted}",
                        )
                        if len(queue) >= wanted:
                            break
                    except (StaleElementReferenceException, Exception):
                        continue

                empty_rounds = empty_rounds + 1 if len(queue) == before else 0
                try:
                    area = self.browser.execute_script(
                        """
                        const d=arguments[0];
                        const a=[...d.querySelectorAll('div')]
                          .filter(x=>x.scrollHeight>x.clientHeight+40)
                          .sort((x,y)=>y.scrollHeight-x.scrollHeight);
                        return a[0]||d;
                        """,
                        dialog,
                    )
                    self.browser.execute_script(
                        "arguments[0].scrollTop=arguments[0].scrollHeight;", area
                    )
                except (StaleElementReferenceException, WebDriverException):
                    self.ui(
                        self.log,
                        f"Takipçi penceresi kapatıldı; mevcut {len(queue)} "
                        "kullanıcıyla devam ediliyor.",
                    )
                    break
                self.stop_event.wait(2)

            if not queue:
                raise RuntimeError(
                    "Takipçi penceresinden hiçbir kullanıcı listeye alınamadı."
                )
            self.ui(
                self.set_status,
                f"{len(queue)} kullanıcı listeye alındı; takip işlemi başlıyor.",
            )

            # 2. AŞAMA: Listedeki profilleri Chrome'da sırayla açıp işle.
            completed = 0
            next_action_at = 0.0
            for profile in queue:
                if self.stop_event.is_set():
                    break
                if not self.wait_while_paused():
                    break
                if self.dry_run_var.get():
                    completed += 1
                    self.ui(self.queue_status, profile, "Deneme")
                    self.ui(self.progress.configure, value=completed)
                    continue
                remaining = ceil(next_action_at - time.monotonic())
                if remaining > 0 and not self.wait_interval(
                    remaining, completed, len(queue)
                ):
                    break

                try:
                    self.browser.get(profile)
                    follow = WebDriverWait(self.browser, 15).until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                "//button[normalize-space()='Takip Et' "
                                "or normalize-space()='Follow' "
                                "or .//*[normalize-space()='Takip Et'] "
                                "or .//*[normalize-space()='Follow']]",
                            )
                        )
                    )
                    self.browser.execute_script("arguments[0].click();", follow)
                    next_action_at = time.monotonic() + interval
                    completed += 1
                    self.ui(self.queue_status, profile, "Takip edildi")
                    self.ui(self.progress.configure, value=completed)
                    self.ui(
                        self.log,
                        f"{completed}/{len(queue)} — {profile.rstrip('/').rsplit('/', 1)[-1]} takip edildi.",
                    )
                except TimeoutException:
                    self.ui(self.queue_status, profile, "Atlandı")
                    self.ui(
                        self.log,
                        f"{profile.rstrip('/').rsplit('/', 1)[-1]} takip edilemedi veya zaten takipte.",
                    )

            final = (
                f"İşlem durduruldu. {completed} kişi takip edildi."
                if self.stop_event.is_set()
                else f"Tamamlandı. {completed} kişi takip edildi."
            )
            self.ui(self.set_status, final)
            self.ui(self.notify, "Instagram Takipçi Paneli", final)
        except TimeoutException:
            self.ui(self.set_status, "Takipçiler penceresi açılmadı.")
        except WebDriverException as exc:
            self.save_diagnostics(exc)
            self.ui(
                self.set_status,
                "Tarayıcı oturumu kullanılamadı. Chrome'u kapatıp tekrar Başlat'a bas.",
            )
        except Exception as exc:
            self.save_diagnostics(exc)
            self.ui(self.set_status, f"Hata: {str(exc).strip() or type(exc).__name__}")
        finally:
            self.running = False
            self.ui(self.start_button.configure, state="normal")
            self.ui(self.stop_button.configure, state="disabled")
            self.ui(self.resume_button.configure, state="normal")

    def pause(self) -> None:
        if not self.running:
            return
        self.pause_event.set()
        self.stop_button.configure(state="disabled")
        self.resume_button.configure(state="normal")
        self.set_status("İşlem duraklatıldı.")
        self.save_session()

    def resume(self) -> None:
        if self.running:
            self.pause_event.clear()
            self.stop_button.configure(state="normal")
            self.resume_button.configure(state="disabled")
            self.set_status("İşlem devam ediyor.")
            return

        pending = []
        for item in self.queue_tree.get_children():
            values = self.queue_tree.item(item, "values")
            if values[2] == "Bekliyor":
                pending.append(f"https://www.instagram.com/{item}/")
        if not pending:
            messagebox.showinfo("Bekleyen işlem yok", "Devam edilecek kullanıcı bulunamadı.")
            return

        self.running = True
        self.stop_event.clear()
        self.pause_event.clear()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.resume_button.configure(state="disabled")
        interval = int(self.interval_var.get())
        threading.Thread(
            target=self.resume_worker, args=(pending, interval), daemon=True
        ).start()

    def resume_worker(self, queue: list[str], interval: int) -> None:
        completed = int(self.completed_var.get())
        try:
            self.ui(self.set_status, "Kayıtlı oturum açılıyor...")
            self.browser = self.ensure_browser()
            self.browser.get("https://www.instagram.com/")
            self.ui(
                self.set_status,
                "Gerekirse Instagram'a giriş yap; bekleyen liste sürdürülecek.",
            )
            time.sleep(5)
            next_action_at = 0.0
            for profile in queue:
                if self.stop_event.is_set() or not self.wait_while_paused():
                    break
                if self.dry_run_var.get():
                    completed += 1
                    self.ui(self.queue_status, profile, "Deneme")
                    self.ui(self.progress.configure, value=completed)
                    continue
                remaining = ceil(next_action_at - time.monotonic())
                if remaining > 0 and not self.wait_interval(
                    remaining, completed, len(queue)
                ):
                    break
                try:
                    self.browser.get(profile)
                    follow = WebDriverWait(self.browser, 15).until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                "//button[normalize-space()='Takip Et' "
                                "or normalize-space()='Follow' "
                                "or .//*[normalize-space()='Takip Et'] "
                                "or .//*[normalize-space()='Follow']]",
                            )
                        )
                    )
                    self.browser.execute_script("arguments[0].click();", follow)
                    next_action_at = time.monotonic() + interval
                    completed += 1
                    self.ui(self.queue_status, profile, "Takip edildi")
                    self.ui(self.progress.configure, value=completed)
                except TimeoutException:
                    self.ui(self.queue_status, profile, "Atlandı")
            self.ui(self.set_status, f"Tamamlandı. Toplam {completed} kişi işlendi.")
            self.ui(
                self.notify,
                "Instagram Takipçi Paneli",
                f"Tamamlandı. Toplam {completed} kişi işlendi.",
            )
        except WebDriverException as exc:
            self.save_diagnostics(exc)
            self.ui(
                self.set_status,
                "Tarayıcı oturumu kullanılamadı. Chrome'u kapatıp tekrar Devam Et'e bas.",
            )
        except Exception as exc:
            self.save_diagnostics(exc)
            self.ui(self.set_status, f"Hata: {str(exc).strip() or type(exc).__name__}")
        finally:
            self.running = False
            self.ui(self.start_button.configure, state="normal")
            self.ui(self.stop_button.configure, state="disabled")
            self.ui(self.resume_button.configure, state="normal")

    def return_to_main_menu(self) -> None:
        if self.running:
            if not messagebox.askyesno(
                "Ana menüye dön",
                "Devam eden takipçi işlemi güvenli şekilde durdurulup ana menüye dönülsün mü?",
            ):
                return
            self.stop_event.set()
            self.pause_event.clear()
            self.set_status("İşlem durduruluyor • Ana menü hazırlanıyor…")
            self._wait_for_main_menu()
            return
        self._open_main_menu()

    def _wait_for_main_menu(self) -> None:
        if self.running:
            self.root.after(200, self._wait_for_main_menu)
            return
        self._open_main_menu()

    def _open_main_menu(self) -> None:
        self.save_session()
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        if self.browser is not None:
            try:
                self.browser.quit()
            except Exception:
                pass
            self.browser = None
        BaslangicMenusu(self.root)

    def close(self) -> None:
        self.stop_event.set()
        self.save_session()
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        if self.browser is not None:
            try:
                self.browser.quit()
            except Exception:
                pass
        self.root.destroy()


def uygulama_simgesini_ayarla(root: tk.Tk) -> None:
    try:
        resource_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        root.iconbitmap(str(resource_dir / "burakhoca_instagram_icon.ico"))
    except (OSError, tk.TclError):
        pass


def pencereyi_temizle(root: tk.Tk) -> None:
    for widget in root.winfo_children():
        widget.destroy()


def tam_ekrani_engelle(root: tk.Tk) -> None:
    """Normal yeniden boyutlandırmayı korurken büyütme/tam ekranı kapat."""
    try:
        root.attributes("-fullscreen", False)
    except tk.TclError:
        pass
    root.bind("<F11>", lambda _event: "break")

    if os.name != "nt":
        return

    def windows_stilini_uygula() -> None:
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            hwnd = root.winfo_id()
            parent = user32.GetParent(hwnd)
            if parent:
                hwnd = parent
            gwl_style = -16
            ws_maximizebox = 0x00010000
            style = user32.GetWindowLongW(hwnd, gwl_style)
            user32.SetWindowLongW(hwnd, gwl_style, style & ~ws_maximizebox)
            user32.SetWindowPos(
                hwnd,
                0,
                0,
                0,
                0,
                0x0020 | 0x0002 | 0x0001 | 0x0004,
            )
        except (OSError, tk.TclError):
            pass

    root.after(80, windows_stilini_uygula)


class BaslangicMenusu:
    """Uygulamanın iki ana modundan birini seçtiren karşılama ekranı."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        pencereyi_temizle(root)
        root.title("Burak Hoca • Instagram Kontrol Merkezi")
        root.geometry("980x650")
        root.minsize(820, 560)
        root.configure(bg="#0b0d17")
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        uygulama_simgesini_ayarla(root)
        tam_ekrani_engelle(root)

        shell = tk.Frame(root, bg="#0b0d17", padx=46, pady=38)
        shell.pack(fill="both", expand=True)

        tk.Label(
            shell,
            text="BURAK HOCA",
            bg="#0b0d17",
            fg="#f472b6",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        tk.Label(
            shell,
            text="Instagram Kontrol Merkezi",
            bg="#0b0d17",
            fg="#ffffff",
            font=("Segoe UI", 29, "bold"),
        ).pack(anchor="w", pady=(5, 4))
        tk.Label(
            shell,
            text="Çalışmak istediğin paneli seç. Her bölüm kendi ekranında açılır.",
            bg="#0b0d17",
            fg="#aeb5cc",
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(0, 28))

        cards = tk.Frame(shell, bg="#0b0d17")
        cards.pack(fill="both", expand=True)
        cards.grid_columnconfigure((0, 1), weight=1, uniform="menu")
        cards.grid_rowconfigure(0, weight=1)

        self.menu_karti(
            cards,
            0,
            "01",
            "Takipçi Otomasyonu",
            "Takipçi listesini al, sıraya koy, aralıklı işle ve yarım kalan oturuma devam et.",
            "#7c3aed",
            self.takipci_panelini_ac,
        )
        self.menu_karti(
            cards,
            1,
            "02",
            "Instagram Yönetim Sistemi",
            "Gönderi ve hikâye hazırla, açıklama ekle, bağlantıyı denetle ve resmî API ile yayınla.",
            "#e1306c",
            self.yonetim_panelini_ac,
        )

        footer = tk.Frame(shell, bg="#0b0d17")
        footer.pack(fill="x", pady=(22, 0))
        tk.Label(
            footer,
            text="@Burakhocafen   •   www.burakhoca.com   •   0552 219 87 87",
            bg="#0b0d17",
            fg="#77809a",
            font=("Segoe UI", 9),
        ).pack(side="left")

    def menu_karti(
        self, parent, column, number, title, description, accent, command
    ) -> None:
        card = tk.Frame(
            parent,
            bg="#151927",
            highlightbackground="#282e43",
            highlightthickness=1,
            padx=26,
            pady=25,
        )
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 10) if column == 0 else (10, 0))
        tk.Label(
            card,
            text=number,
            bg=accent,
            fg="#ffffff",
            font=("Segoe UI", 11, "bold"),
            padx=11,
            pady=7,
        ).pack(anchor="w")
        tk.Label(
            card,
            text=title,
            bg="#151927",
            fg="#ffffff",
            font=("Segoe UI", 20, "bold"),
            wraplength=330,
            justify="left",
        ).pack(anchor="w", pady=(25, 12))
        tk.Label(
            card,
            text=description,
            bg="#151927",
            fg="#aeb5cc",
            font=("Segoe UI", 11),
            wraplength=350,
            justify="left",
        ).pack(anchor="w")
        tk.Button(
            card,
            text="Paneli Aç  →",
            command=command,
            bg=accent,
            fg="#ffffff",
            activebackground=accent,
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 11, "bold"),
            padx=20,
            pady=12,
        ).pack(anchor="w", side="bottom")

    def takipci_panelini_ac(self) -> None:
        pencereyi_temizle(self.root)
        TakipciUygulamasi(self.root)

    def yonetim_panelini_ac(self) -> None:
        pencereyi_temizle(self.root)
        InstagramYonetimPaneli(self.root)


class MetaApiYonetimPaneli:
    """Instagram profesyonel hesapları için resmî içerik yayınlama paneli."""

    VERSION = "3.0.0"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.busy = False
        self.preview_image = None
        self.settings_path = self.data_dir() / "yonetim_ayarlari.json"

        root.title("Burak Hoca • Instagram Yönetim Sistemi")
        root.geometry("1120x820")
        root.minsize(940, 700)
        root.configure(bg="#0b0d17")
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        uygulama_simgesini_ayarla(root)

        self.ig_user_id = tk.StringVar()
        self.api_version = tk.StringVar(value="v26.0")
        self.access_token = tk.StringVar()
        self.media_url = tk.StringVar()
        self.content_type = tk.StringVar(value="Gönderi")
        self.status = tk.StringVar(value="Hazır • Önce bağlantı ayarlarını girip hesabı test et.")
        self.load_settings()
        self.build_ui()

    @staticmethod
    def data_dir() -> Path:
        executable_dir = Path(
            sys.executable if getattr(sys, "frozen", False) else __file__
        ).parent
        folder = (
            Path(os.environ.get("LOCALAPPDATA", str(executable_dir)))
            / "BurakHocaInstagramPaneli"
        )
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def build_ui(self) -> None:
        outer = tk.Frame(self.root, bg="#0b0d17", padx=28, pady=24)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg="#151927", padx=20, pady=16)
        header.pack(fill="x")
        tk.Button(
            header,
            text="← Ana Menü",
            command=self.back_to_menu,
            bg="#282e43",
            fg="#ffffff",
            activebackground="#343b52",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=9,
        ).pack(side="left")
        title_box = tk.Frame(header, bg="#151927")
        title_box.pack(side="left", padx=18)
        tk.Label(
            title_box,
            text="Instagram Yönetim Sistemi",
            bg="#151927",
            fg="#ffffff",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text="Gönderi • Hikâye • Açıklama • Resmî Meta API",
            bg="#151927",
            fg="#aeb5cc",
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="● GÜVENLİ API MODU",
            bg="#15251e",
            fg="#4ade80",
            font=("Segoe UI", 9, "bold"),
            padx=13,
            pady=9,
        ).pack(side="right")

        connection = tk.LabelFrame(
            outer,
            text="  Hesap Bağlantısı  ",
            bg="#111521",
            fg="#f8fafc",
            font=("Segoe UI", 10, "bold"),
            bd=0,
            padx=16,
            pady=13,
        )
        connection.pack(fill="x", pady=(16, 12))
        for col in range(6):
            connection.grid_columnconfigure(col, weight=1 if col in (1, 3) else 0)
        self.field_label(connection, "Instagram User ID", 0, 0)
        tk.Entry(
            connection,
            textvariable=self.ig_user_id,
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief="flat",
            font=("Segoe UI", 10),
        ).grid(row=0, column=1, sticky="ew", padx=(8, 18), ipady=7)
        self.field_label(connection, "API sürümü", 0, 2)
        tk.Entry(
            connection,
            textvariable=self.api_version,
            width=10,
            bg="#ffffff",
            fg="#111827",
            relief="flat",
            font=("Segoe UI", 10),
        ).grid(row=0, column=3, sticky="ew", padx=(8, 18), ipady=7)
        self.field_label(connection, "Erişim anahtarı", 1, 0)
        tk.Entry(
            connection,
            textvariable=self.access_token,
            show="●",
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief="flat",
            font=("Segoe UI", 10),
        ).grid(row=1, column=1, columnspan=3, sticky="ew", padx=(8, 18), pady=(10, 0), ipady=7)
        self.test_button = self.action_button(
            connection, "Bağlantıyı Test Et", self.test_connection, "#2563eb"
        )
        self.test_button.grid(row=0, column=4, rowspan=2, sticky="ns", padx=(4, 0))

        content = tk.Frame(outer, bg="#0b0d17")
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        editor = tk.LabelFrame(
            content,
            text="  İçerik Hazırla  ",
            bg="#151927",
            fg="#f8fafc",
            font=("Segoe UI", 10, "bold"),
            bd=0,
            padx=18,
            pady=15,
        )
        editor.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        editor.grid_columnconfigure(1, weight=1)
        self.field_label(editor, "İçerik türü", 0, 0)
        type_box = ttk.Combobox(
            editor,
            textvariable=self.content_type,
            values=("Gönderi", "Hikâye"),
            state="readonly",
            width=18,
        )
        type_box.grid(row=0, column=1, sticky="w", padx=(12, 0), pady=5)
        type_box.bind("<<ComboboxSelected>>", self.content_type_changed)

        self.field_label(editor, "Medya HTTPS adresi", 1, 0)
        tk.Entry(
            editor,
            textvariable=self.media_url,
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief="flat",
            font=("Segoe UI", 10),
        ).grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=5, ipady=8)
        tk.Label(
            editor,
            text="Instagram medyayı bu adresten alır; bağlantı herkese açık olmalıdır.",
            bg="#151927",
            fg="#8f98b2",
            font=("Segoe UI", 9),
        ).grid(row=2, column=1, sticky="w", padx=(12, 0))

        self.caption_label = tk.Label(
            editor,
            text="Açıklama",
            bg="#151927",
            fg="#dbe0ef",
            font=("Segoe UI", 10, "bold"),
        )
        self.caption_label.grid(row=3, column=0, sticky="nw", pady=(14, 0))
        caption_frame = tk.Frame(editor, bg="#151927")
        caption_frame.grid(row=3, column=1, sticky="nsew", padx=(12, 0), pady=(14, 0))
        editor.grid_rowconfigure(3, weight=1)
        self.caption = tk.Text(
            caption_frame,
            height=12,
            wrap="word",
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief="flat",
            font=("Segoe UI", 10),
            padx=10,
            pady=9,
        )
        self.caption.pack(fill="both", expand=True)
        self.caption.bind("<KeyRelease>", self.update_character_count)
        self.character_count = tk.Label(
            caption_frame,
            text="0 / 2.200",
            bg="#151927",
            fg="#8f98b2",
            font=("Segoe UI", 9),
        )
        self.character_count.pack(anchor="e", pady=(5, 0))

        actions = tk.Frame(editor, bg="#151927")
        actions.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        self.publish_button = self.action_button(
            actions, "İçeriği Şimdi Yayınla", self.publish_content, "#e1306c"
        )
        self.publish_button.pack(side="left")
        self.action_button(
            actions, "Alanları Temizle", self.clear_editor, "#343b52"
        ).pack(side="left", padx=9)

        side = tk.Frame(content, bg="#0b0d17")
        side.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        info = tk.LabelFrame(
            side,
            text="  Yayın Kontrolü  ",
            bg="#111521",
            fg="#f8fafc",
            font=("Segoe UI", 10, "bold"),
            bd=0,
            padx=16,
            pady=14,
        )
        info.pack(fill="x")
        tk.Label(
            info,
            textvariable=self.status,
            bg="#111521",
            fg="#dbe0ef",
            font=("Segoe UI", 10),
            wraplength=350,
            justify="left",
        ).pack(anchor="w")
        self.progress = ttk.Progressbar(info, mode="indeterminate")
        self.progress.pack(fill="x", pady=(13, 0))

        guide = tk.LabelFrame(
            side,
            text="  Gerekenler  ",
            bg="#151927",
            fg="#f8fafc",
            font=("Segoe UI", 10, "bold"),
            bd=0,
            padx=16,
            pady=14,
        )
        guide.pack(fill="x", pady=12)
        tk.Label(
            guide,
            text=(
                "• Instagram İşletme veya İçerik Üreticisi hesabı\n"
                "• Meta uygulaması ve içerik yayınlama izni\n"
                "• Instagram User ID ve geçerli erişim anahtarı\n"
                "• Herkese açık HTTPS medya bağlantısı\n\n"
                "Güvenlik: erişim anahtarı bilgisayara kaydedilmez."
            ),
            bg="#151927",
            fg="#aeb5cc",
            font=("Segoe UI", 9),
            justify="left",
            wraplength=350,
        ).pack(anchor="w")

        log_box = tk.LabelFrame(
            side,
            text="  Yayın Günlüğü  ",
            bg="#111521",
            fg="#f8fafc",
            font=("Segoe UI", 10, "bold"),
            bd=0,
            padx=12,
            pady=10,
        )
        log_box.pack(fill="both", expand=True)
        self.log_text = tk.Text(
            log_box,
            height=10,
            state="disabled",
            wrap="word",
            bg="#090c14",
            fg="#cbd5e1",
            relief="flat",
            font=("Consolas", 9),
            padx=9,
            pady=8,
        )
        self.log_text.pack(fill="both", expand=True)
        self.log("Instagram yönetim paneli hazır.")

    @staticmethod
    def field_label(parent, text, row, column) -> None:
        tk.Label(
            parent,
            text=text,
            bg=parent.cget("bg"),
            fg="#dbe0ef",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=row, column=column, sticky="w", pady=5)

    @staticmethod
    def action_button(parent, text, command, color) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="#ffffff",
            activebackground=color,
            activeforeground="#ffffff",
            disabledforeground="#9ca3af",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=17,
            pady=10,
        )

    def content_type_changed(self, _event=None) -> None:
        story = self.content_type.get() == "Hikâye"
        self.caption.configure(fg="#667085" if story else "#dbe0ef")
        self.caption.configure(state="disabled" if story else "normal")
        if story:
            self.status.set("Hikâyelerde açıklama kullanılmaz; medya bağlantısı yayınlanır.")
        else:
            self.status.set("Gönderi için medya bağlantısı ve isteğe bağlı açıklama hazırla.")

    def update_character_count(self, _event=None) -> None:
        count = len(self.caption.get("1.0", "end-1c"))
        self.character_count.configure(
            text=f"{count:,} / 2.200".replace(",", "."),
            fg="#fb7185" if count > 2200 else "#8f98b2",
        )

    def clear_editor(self) -> None:
        self.media_url.set("")
        self.caption.configure(state="normal")
        self.caption.delete("1.0", "end")
        self.content_type.set("Gönderi")
        self.update_character_count()
        self.status.set("İçerik alanları temizlendi.")

    def load_settings(self) -> None:
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            self.ig_user_id.set(str(data.get("ig_user_id", "")))
            self.api_version.set(str(data.get("api_version", "v26.0")))
        except (OSError, ValueError, TypeError):
            pass

    def save_settings(self) -> None:
        data = {
            "ig_user_id": self.ig_user_id.get().strip(),
            "api_version": self.api_version.get().strip(),
        }
        self.settings_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def validate_connection_fields(self) -> tuple[str, str, str]:
        ig_id = self.ig_user_id.get().strip()
        version = self.api_version.get().strip()
        token = self.access_token.get().strip()
        if not ig_id or not version or not token:
            raise ValueError("Instagram User ID, API sürümü ve erişim anahtarı zorunludur.")
        if not version.startswith("v"):
            version = f"v{version}"
        return ig_id, version, token

    @staticmethod
    def api_request(url: str, token: str, data: dict | None = None) -> dict:
        body = urlencode(data).encode("utf-8") if data is not None else None
        request = Request(
            url,
            data=body,
            method="POST" if body is not None else "GET",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "BurakHoca-InstagramPaneli/3.0",
            },
        )
        try:
            with urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw).get("error", {}).get("message", raw)
            except ValueError:
                detail = raw
            raise RuntimeError(f"Instagram API hatası ({exc.code}): {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Bağlantı kurulamadı: {exc.reason}") from exc

    def run_job(self, label: str, work) -> None:
        if self.busy:
            messagebox.showinfo("İşlem sürüyor", "Lütfen devam eden işlemin bitmesini bekle.")
            return
        self.busy = True
        self.publish_button.configure(state="disabled")
        self.test_button.configure(state="disabled")
        self.progress.start(12)
        self.status.set(label)
        self.log(label)

        def runner() -> None:
            try:
                result = work()
                self.root.after(0, lambda: self.job_finished(result, None))
            except Exception as exc:
                self.root.after(0, lambda: self.job_finished(None, exc))

        threading.Thread(target=runner, daemon=True).start()

    def job_finished(self, result, error) -> None:
        self.busy = False
        self.progress.stop()
        self.publish_button.configure(state="normal")
        self.test_button.configure(state="normal")
        if error:
            text = str(error).strip() or type(error).__name__
            self.status.set(f"Hata: {text}")
            self.log(f"HATA • {text}")
            messagebox.showerror("Instagram işlemi tamamlanamadı", text)
            return
        self.status.set(result)
        self.log(result)

    def test_connection(self) -> None:
        def work() -> str:
            ig_id, version, token = self.validate_connection_fields()
            url = f"https://graph.instagram.com/{version}/{ig_id}?fields=id,username"
            result = self.api_request(url, token)
            self.save_settings()
            return f"Bağlantı başarılı • @{result.get('username', ig_id)}"

        self.run_job("Instagram hesabı kontrol ediliyor…", work)

    def validate_media_url(self) -> str:
        url = self.media_url.get().strip()
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Medya için herkese açık, doğrudan bir HTTPS bağlantısı gir.")
        return url

    def publish_content(self) -> None:
        kind = self.content_type.get()
        if not messagebox.askyesno(
            "Yayın onayı",
            f"Bu {kind.lower()} Instagram hesabında şimdi yayınlansın mı?",
        ):
            return

        def work() -> str:
            ig_id, version, token = self.validate_connection_fields()
            media_url = self.validate_media_url()
            caption = self.caption.get("1.0", "end-1c").strip()
            if len(caption) > 2200:
                raise ValueError("Açıklama 2.200 karakterden uzun olamaz.")
            endpoint = f"https://graph.instagram.com/{version}/{ig_id}"
            payload: dict[str, str] = {}
            if kind == "Hikâye":
                extension = Path(urlparse(media_url).path).suffix.casefold()
                if extension in {".mp4", ".mov", ".m4v"}:
                    payload.update({"media_type": "STORIES", "video_url": media_url})
                else:
                    payload.update({"media_type": "STORIES", "image_url": media_url})
            else:
                payload["image_url"] = media_url
                if caption:
                    payload["caption"] = caption
            self.root.after(0, lambda: self.status.set("Medya kapsayıcısı hazırlanıyor…"))
            container = self.api_request(f"{endpoint}/media", token, payload)
            creation_id = container.get("id")
            if not creation_id:
                raise RuntimeError("Instagram medya kapsayıcısı kimliği döndürmedi.")
            self.root.after(0, lambda: self.status.set("İçerik Instagram'da yayınlanıyor…"))
            published = self.api_request(
                f"{endpoint}/media_publish", token, {"creation_id": creation_id}
            )
            media_id = published.get("id")
            self.save_settings()
            return f"{kind} başarıyla yayınlandı • Medya ID: {media_id or 'alındı'}"

        self.run_job(f"{kind} yayına hazırlanıyor…", work)

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def back_to_menu(self) -> None:
        if self.busy:
            messagebox.showwarning(
                "İşlem sürüyor", "Yayın işlemi tamamlanmadan ana menüye dönemezsin."
            )
            return
        BaslangicMenusu(self.root)


class InstagramYonetimPaneli:
    """Yerel medya dosyalarını kayıtlı Chrome oturumuyla zamanlı yayınlar."""

    VERSION = "3.4.0"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.browser: Chrome | None = None
        self.running = False
        self.closed = False
        self.stop_event = threading.Event()
        self.selected_file = tk.StringVar()
        self.content_type = tk.StringVar(value="Gönderi")
        now = datetime.now() + timedelta(minutes=5)
        self.publish_date = tk.StringVar(value=now.strftime("%d.%m.%Y"))
        self.publish_time = tk.StringVar(value=now.strftime("%H:%M"))
        self.status = tk.StringVar(value="Hazır • Bir görsel seçip yayın zamanını belirle.")
        self.waiting_count = tk.StringVar(value="0")
        self.published_count = tk.StringVar(value="0")
        self.failed_count = tk.StringVar(value="0")
        self.data_path = uygulama_veri_klasoru() / "yayin_kuyrugu.json"
        self.queue: list[dict] = self.load_queue()

        root.title("Burak Hoca • Instagram Yönetim Sistemi")
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = min(1180, max(760, screen_width - 100))
        window_height = min(860, max(560, screen_height - 120))
        left = max(0, (screen_width - window_width) // 2)
        top = max(0, (screen_height - window_height) // 2)
        root.geometry(f"{window_width}x{window_height}+{left}+{top}")
        root.minsize(min(760, screen_width), min(560, screen_height))
        root.configure(bg="#0b0d17")
        root.protocol("WM_DELETE_WINDOW", self.close)
        uygulama_simgesini_ayarla(root)
        tam_ekrani_engelle(root)
        self.build_ui()
        self.refresh_queue()
        self.root.after(1000, self.scheduler_tick)

    def build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Manager.TCombobox",
            fieldbackground="#ffffff",
            background="#30364a",
            foreground="#111827",
            arrowcolor="#ffffff",
            borderwidth=0,
            padding=7,
        )
        style.configure(
            "Manager.Treeview",
            background="#101420",
            fieldbackground="#101420",
            foreground="#e8ecf5",
            rowheight=32,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Manager.Treeview.Heading",
            background="#242a3c",
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padding=8,
            borderwidth=0,
        )
        style.map(
            "Manager.Treeview",
            background=[("selected", "#7c3aed")],
            foreground=[("selected", "#ffffff")],
        )
        viewport = tk.Frame(self.root, bg="#0b0d17")
        viewport.pack(fill="both", expand=True)
        self.scroll_canvas = tk.Canvas(
            viewport,
            bg="#0b0d17",
            highlightthickness=0,
            borderwidth=0,
        )
        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        outer = tk.Frame(self.scroll_canvas, bg="#0b0d17", padx=22, pady=18)
        self.management_outer = outer
        self.canvas_window = self.scroll_canvas.create_window(
            (0, 0), window=outer, anchor="nw"
        )
        outer.bind(
            "<Configure>",
            lambda _event: self.scroll_canvas.configure(
                scrollregion=self.scroll_canvas.bbox("all")
            ),
        )
        self.scroll_canvas.bind("<Configure>", self.resize_management_layout)
        header = tk.Frame(outer, bg="#151927", padx=20, pady=15)
        self.management_header = header
        header.pack(fill="x")
        self.button(header, "← Ana Menü", self.back_to_menu, "#30364a").pack(side="left")
        titles = tk.Frame(header, bg="#151927")
        titles.pack(side="left", padx=18)
        tk.Label(
            titles, text="Instagram Yönetim Sistemi", bg="#151927", fg="#ffffff",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")
        tk.Label(
            titles, text="Bilgisayardan seç • Tarih ve saati belirle • Chrome ile yayınla",
            bg="#151927", fg="#aeb5cc", font=("Segoe UI", 10)
        ).pack(anchor="w")
        self.automation_badge = tk.Label(
            header, text="● TARAYICI OTOMASYONU", bg="#17251f", fg="#4ade80",
            font=("Segoe UI", 9, "bold"), padx=13, pady=9
        )
        self.automation_badge.pack(side="right")

        body = tk.Frame(outer, bg="#0b0d17")
        body.pack(fill="both", expand=True, pady=(15, 0))
        self.management_body = body
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        editor = tk.LabelFrame(
            body, text="  Yeni İçerik Planla  ", bg="#151927", fg="#ffffff",
            font=("Segoe UI", 10, "bold"), bd=0, padx=18, pady=16
        )
        self.management_editor = editor
        editor.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        editor.grid_columnconfigure(1, weight=1)
        self.label(editor, "İçerik türü", 0)
        ttk.Combobox(
            editor, textvariable=self.content_type, values=("Gönderi",),
            state="readonly", width=18, style="Manager.TCombobox"
        ).grid(row=0, column=1, sticky="w", padx=(12, 0), pady=6)
        tk.Label(
            editor,
            text="Hikâye paylaşımı Instagram web kısıtlaması nedeniyle devre dışıdır.",
            bg="#151927",
            fg="#8f98b2",
            font=("Segoe UI", 8),
        ).grid(row=0, column=1, sticky="w", padx=(170, 0), pady=6)

        self.label(editor, "Medya dosyası", 1)
        file_row = tk.Frame(editor, bg="#151927")
        file_row.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=6)
        file_row.grid_columnconfigure(0, weight=1)
        tk.Entry(
            file_row, textvariable=self.selected_file, state="readonly",
            readonlybackground="#ffffff", fg="#111827", relief="flat",
            font=("Segoe UI", 10)
        ).grid(row=0, column=0, sticky="ew", ipady=8)
        self.button(file_row, "Dosya Seç", self.select_file, "#7c3aed").grid(
            row=0, column=1, padx=(8, 0)
        )

        self.label(editor, "Yayın tarihi", 2)
        schedule = tk.Frame(editor, bg="#151927")
        schedule.grid(row=2, column=1, sticky="w", padx=(12, 0), pady=6)
        tk.Entry(
            schedule, textvariable=self.publish_date, width=15, bg="#ffffff",
            fg="#111827", relief="flat", font=("Segoe UI", 10), justify="center"
        ).pack(side="left", ipady=8)
        tk.Label(
            schedule, text="Saat", bg="#151927", fg="#dbe0ef",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=(18, 8))
        tk.Entry(
            schedule, textvariable=self.publish_time, width=9, bg="#ffffff",
            fg="#111827", relief="flat", font=("Segoe UI", 10), justify="center"
        ).pack(side="left", ipady=8)
        self.mini_button(schedule, "+15 dk", lambda: self.quick_time(15)).pack(
            side="left", padx=(12, 4)
        )
        self.mini_button(schedule, "+1 saat", lambda: self.quick_time(60)).pack(
            side="left", padx=4
        )
        self.mini_button(schedule, "Yarın 10:00", self.tomorrow_morning).pack(
            side="left", padx=4
        )
        tk.Label(
            editor, text="Tarih: GG.AA.YYYY   •   Saat: SS:DD",
            bg="#151927", fg="#8f98b2", font=("Segoe UI", 9)
        ).grid(row=3, column=1, sticky="w", padx=(12, 0))

        self.label(editor, "Açıklama", 4, sticky="nw")
        self.caption = tk.Text(
            editor, height=13, wrap="word", bg="#ffffff", fg="#111827",
            insertbackground="#111827", relief="flat", font=("Segoe UI", 10),
            padx=10, pady=9
        )
        self.caption.grid(row=4, column=1, sticky="nsew", padx=(12, 0), pady=(12, 4))
        editor.grid_rowconfigure(4, weight=1)
        self.caption.bind("<KeyRelease>", self.update_count)
        self.counter = tk.Label(
            editor, text="0 / 2.200", bg="#151927", fg="#8f98b2",
            font=("Segoe UI", 9)
        )
        self.counter.grid(row=5, column=1, sticky="e")

        actions = tk.Frame(editor, bg="#151927")
        actions.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(15, 0))
        self.button(actions, "Planlamaya Ekle", self.add_schedule, "#e1306c").pack(side="left")
        self.button(actions, "Şimdi Paylaş", self.publish_now, "#2563eb").pack(
            side="left", padx=8
        )
        self.button(actions, "Chrome'u Aç", self.open_chrome, "#343b52").pack(side="left")
        helpers = tk.Frame(editor, bg="#151927")
        helpers.grid(row=6, column=1, sticky="ew", padx=(12, 0), pady=(5, 0))
        self.mini_button(helpers, "Tanıtım Şablonu", self.insert_promo_caption).pack(
            side="left"
        )
        self.mini_button(helpers, "Etiket Öner", self.insert_hashtags).pack(
            side="left", padx=6
        )
        self.mini_button(helpers, "Açıklamayı Temizle", self.clear_caption).pack(
            side="left"
        )

        side = tk.Frame(body, bg="#0b0d17")
        self.management_side = side
        side.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        status_box = tk.LabelFrame(
            side, text="  Sistem Durumu  ", bg="#111521", fg="#ffffff",
            font=("Segoe UI", 10, "bold"), bd=0, padx=14, pady=13
        )
        status_box.pack(fill="x")
        tk.Label(
            status_box, textvariable=self.status, bg="#111521", fg="#dbe0ef",
            font=("Segoe UI", 10), wraplength=390, justify="left"
        ).pack(anchor="w")
        self.progress = ttk.Progressbar(status_box, mode="indeterminate")
        self.progress.pack(fill="x", pady=(12, 0))

        preview_box = tk.Frame(
            side, bg="#151927", highlightbackground="#282e43",
            highlightthickness=1, height=178
        )
        self.preview_box = preview_box
        preview_box.pack(fill="x", pady=(12, 0))
        preview_box.pack_propagate(False)
        self.preview_label = tk.Label(
            preview_box,
            text="MEDYA ÖNİZLEME\n\nHenüz dosya seçilmedi",
            bg="#151927",
            fg="#77809a",
            font=("Segoe UI", 9, "bold"),
            justify="center",
        )
        self.preview_label.pack(fill="both", expand=True, padx=8, pady=8)

        queue_box = tk.LabelFrame(
            side, text="  Planlanan Yayınlar  ", bg="#151927", fg="#ffffff",
            font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=10
        )
        queue_box.pack(fill="both", expand=True, pady=(12, 0))
        queue_stats = tk.Frame(queue_box, bg="#151927")
        queue_stats.pack(fill="x", pady=(0, 9))
        self.queue_stat(queue_stats, "BEKLEYEN", self.waiting_count, "#fbbf24")
        self.queue_stat(queue_stats, "YAYINLANAN", self.published_count, "#4ade80")
        self.queue_stat(queue_stats, "HATALI", self.failed_count, "#fb7185", last=True)
        self.queue_tree = ttk.Treeview(
            queue_box, columns=("type", "time", "status"), show="headings", height=8,
            style="Manager.Treeview"
        )
        self.queue_tree.heading("type", text="Tür")
        self.queue_tree.heading("time", text="Yayın Zamanı")
        self.queue_tree.heading("status", text="Durum")
        self.queue_tree.column("type", width=75, anchor="center")
        self.queue_tree.column("time", width=140, anchor="center")
        self.queue_tree.column("status", width=105, anchor="center")
        self.queue_tree.pack(fill="both", expand=True)
        self.queue_tree.bind("<Double-1>", lambda _event: self.load_selected_to_editor())
        self.queue_tree.bind("<Delete>", lambda _event: self.delete_selected())
        queue_actions = tk.Frame(queue_box, bg="#151927")
        queue_actions.pack(fill="x", pady=(9, 0))
        self.button(queue_actions, "Seçileni Sil", self.delete_selected, "#7f1d3a").pack(
            side="left"
        )
        self.button(queue_actions, "Başarısızları Dene", self.retry_failed, "#343b52").pack(
            side="left", padx=7
        )
        self.button(queue_actions, "Editöre Al", self.load_selected_to_editor, "#2563eb").pack(
            side="left"
        )
        tk.Label(
            side,
            text=(
                "Program ve bilgisayar planlanan saatte açık olmalıdır. İlk kullanımda "
                "açılan Chrome'da Instagram hesabına giriş yap. Gönderi sırasında "
                "tarayıcı penceresini kapatma."
            ),
            bg="#0b0d17", fg="#8f98b2", font=("Segoe UI", 9),
            wraplength=405, justify="left"
        ).pack(fill="x", pady=(12, 0))

    @staticmethod
    def button(parent, text, command, color) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command, bg=color, fg="#ffffff",
            activebackground=color, activeforeground="#ffffff", relief="flat",
            cursor="hand2", font=("Segoe UI", 9, "bold"), padx=14, pady=9
        )

    def resize_management_layout(self, event) -> None:
        self.scroll_canvas.itemconfigure(
            self.canvas_window, width=max(1, event.width)
        )
        if not all(
            hasattr(self, name)
            for name in ("management_body", "management_editor", "management_side")
        ):
            return
        if event.height < 700:
            caption_height, preview_height, queue_height = 4, 60, 2
            self.management_outer.configure(padx=12, pady=8)
            self.management_header.configure(padx=12, pady=8)
            self.management_body.pack_configure(pady=(7, 0))
            self.management_editor.configure(padx=12, pady=9)
        elif event.height < 850:
            caption_height, preview_height, queue_height = 6, 82, 3
            self.management_outer.configure(padx=16, pady=11)
            self.management_header.configure(padx=15, pady=10)
            self.management_body.pack_configure(pady=(9, 0))
            self.management_editor.configure(padx=14, pady=11)
        elif event.height < 980:
            caption_height, preview_height, queue_height = 9, 126, 5
            self.management_outer.configure(padx=20, pady=15)
            self.management_header.configure(padx=18, pady=13)
            self.management_body.pack_configure(pady=(12, 0))
            self.management_editor.configure(padx=16, pady=14)
        else:
            caption_height, preview_height, queue_height = 12, 160, 7
            self.management_outer.configure(padx=22, pady=18)
            self.management_header.configure(padx=20, pady=15)
            self.management_body.pack_configure(pady=(15, 0))
            self.management_editor.configure(padx=18, pady=16)
        self.caption.configure(height=caption_height)
        self.preview_box.configure(height=preview_height)
        self.queue_tree.configure(height=queue_height)
        compact = event.width < 1050
        if event.width < 820:
            self.automation_badge.pack_forget()
        elif not self.automation_badge.winfo_manager():
            self.automation_badge.pack(side="right")
        if getattr(self, "_compact_layout", None) == compact:
            return
        self._compact_layout = compact
        body = self.management_body
        editor = self.management_editor
        side = self.management_side
        editor.grid_forget()
        side.grid_forget()
        if compact:
            body.grid_columnconfigure(0, weight=1)
            body.grid_columnconfigure(1, weight=0)
            body.grid_rowconfigure(0, weight=0)
            body.grid_rowconfigure(1, weight=0)
            editor.grid(row=0, column=0, sticky="ew")
            side.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        else:
            body.grid_columnconfigure(0, weight=3)
            body.grid_columnconfigure(1, weight=2)
            body.grid_rowconfigure(0, weight=1)
            body.grid_rowconfigure(1, weight=0)
            editor.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
            side.grid(row=0, column=1, sticky="nsew", padx=(7, 0), pady=0)
        self.root.after_idle(
            lambda: self.scroll_canvas.configure(
                scrollregion=self.scroll_canvas.bbox("all")
            )
        )

    def scroll_management_panel(self, event) -> None:
        if not self.scroll_canvas.winfo_exists():
            return
        direction = -1 if event.delta > 0 else 1
        self.scroll_canvas.yview_scroll(direction * 3, "units")

    def release_scroll_binding(self) -> None:
        try:
            self.root.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass

    @staticmethod
    def mini_button(parent, text, command) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg="#252b3d",
            fg="#dbe0ef",
            activebackground="#343b52",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 8, "bold"),
            padx=9,
            pady=6,
        )

    @staticmethod
    def queue_stat(parent, title, variable, color, last=False) -> None:
        card = tk.Frame(
            parent,
            bg="#101420",
            highlightbackground="#282e43",
            highlightthickness=1,
            padx=10,
            pady=7,
        )
        card.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 0 if last else 6),
        )
        tk.Label(
            card, text=title, bg="#101420", fg="#77809a",
            font=("Segoe UI", 7, "bold")
        ).pack(anchor="w")
        tk.Label(
            card, textvariable=variable, bg="#101420", fg=color,
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w")

    @staticmethod
    def label(parent, text, row, sticky="w") -> None:
        tk.Label(
            parent, text=text, bg="#151927", fg="#dbe0ef",
            font=("Segoe UI", 10, "bold")
        ).grid(row=row, column=0, sticky=sticky, pady=6)

    def select_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Instagram medyasını seç",
            filetypes=[
                ("Desteklenen medya", "*.jpg *.jpeg *.png *.mp4"),
                ("Resimler", "*.jpg *.jpeg *.png"),
                ("Videolar", "*.mp4"),
            ],
        )
        if path:
            self.selected_file.set(str(Path(path).resolve()))
            self.status.set(f"Medya seçildi • {Path(path).name}")
            self.show_preview(path)

    def show_preview(self, path: str) -> None:
        media = Path(path)
        if media.suffix.casefold() == ".mp4":
            self.preview_image = None
            self.preview_label.configure(
                image="",
                text=f"VİDEO DOSYASI\n\n{media.name}",
                fg="#c4b5fd",
            )
            return
        try:
            image = Image.open(media)
            image.thumbnail((380, 155), Image.Resampling.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=self.preview_image, text="")
        except (OSError, ValueError):
            self.preview_image = None
            self.preview_label.configure(
                image="", text=f"Önizleme oluşturulamadı\n\n{media.name}", fg="#fb7185"
            )

    def quick_time(self, minutes: int) -> None:
        target = datetime.now() + timedelta(minutes=minutes)
        self.publish_date.set(target.strftime("%d.%m.%Y"))
        self.publish_time.set(target.strftime("%H:%M"))
        self.status.set(f"Yayın zamanı {minutes} dakika sonrası olarak ayarlandı.")

    def tomorrow_morning(self) -> None:
        target = (datetime.now() + timedelta(days=1)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        self.publish_date.set(target.strftime("%d.%m.%Y"))
        self.publish_time.set(target.strftime("%H:%M"))
        self.status.set("Yayın zamanı yarın 10:00 olarak ayarlandı.")

    def insert_promo_caption(self) -> None:
        template = (
            "Yeni içeriğimiz yayında! ✨\n\n"
            "Detaylı bilgi için bizimle iletişime geçebilirsiniz.\n"
            "🌐 www.burakhoca.com\n"
            "📱 0552 219 87 87\n"
            "📸 @burakhocafen"
        )
        self.caption.delete("1.0", "end")
        self.caption.insert("1.0", template)
        self.update_count()

    def insert_hashtags(self) -> None:
        tags = (
            "\n\n#burakhoca #dijitaleğitim #sosyalmedya "
            "#instagram #içeriküretimi #dijitalpazarlama"
        )
        current = self.caption.get("1.0", "end-1c")
        if "#burakhoca" not in current.casefold():
            self.caption.insert("end", tags)
            self.update_count()

    def clear_caption(self) -> None:
        self.caption.delete("1.0", "end")
        self.update_count()

    def update_count(self, _event=None) -> None:
        count = len(self.caption.get("1.0", "end-1c"))
        self.counter.configure(
            text=f"{count:,} / 2.200".replace(",", "."),
            fg="#fb7185" if count > 2200 else "#8f98b2",
        )

    def form_data(self, immediate=False) -> dict:
        media = Path(self.selected_file.get())
        if not media.is_file():
            raise ValueError("Önce paylaşılacak resim veya videoyu seç.")
        if self.content_type.get() == "Hikâye":
            raise ValueError(
                "Hikâye paylaşımı Instagram web kısıtlaması nedeniyle devre dışıdır."
            )
        if (
            self.content_type.get() == "Hikâye"
            and media.suffix.casefold() not in {".jpg", ".jpeg", ".png"}
        ):
            raise ValueError(
                "API'siz mobil web hikâye paylaşımında JPG veya PNG görsel seç."
            )
        caption = self.caption.get("1.0", "end-1c").strip()
        if len(caption) > 2200:
            raise ValueError("Açıklama 2.200 karakterden uzun olamaz.")
        if immediate:
            publish_at = datetime.now()
        else:
            try:
                publish_at = datetime.strptime(
                    f"{self.publish_date.get().strip()} {self.publish_time.get().strip()}",
                    "%d.%m.%Y %H:%M",
                )
            except ValueError as exc:
                raise ValueError("Tarih GG.AA.YYYY, saat SS:DD biçiminde olmalı.") from exc
            if publish_at <= datetime.now():
                raise ValueError("Planlanan zaman şu andan ileride olmalı.")
        return {
            "id": f"{time.time_ns()}",
            "type": self.content_type.get(),
            "media": str(media),
            "caption": caption,
            "publish_at": publish_at.isoformat(timespec="minutes"),
            "status": "Bekliyor",
            "error": "",
        }

    def add_schedule(self) -> None:
        try:
            item = self.form_data()
        except ValueError as exc:
            messagebox.showwarning("Eksik veya hatalı bilgi", str(exc))
            return
        self.queue.append(item)
        self.save_queue()
        self.refresh_queue()
        self.clear_form()
        self.status.set("İçerik yayın kuyruğuna eklendi.")

    def publish_now(self) -> None:
        try:
            item = self.form_data(immediate=True)
        except ValueError as exc:
            messagebox.showwarning("Eksik veya hatalı bilgi", str(exc))
            return
        if not messagebox.askyesno("Yayın onayı", "İçerik şimdi Instagram'da paylaşılsın mı?"):
            return
        self.queue.append(item)
        self.save_queue()
        self.refresh_queue()
        self.start_publish(item)

    def clear_form(self) -> None:
        self.selected_file.set("")
        self.caption.delete("1.0", "end")
        self.preview_image = None
        self.preview_label.configure(
            image="",
            text="MEDYA ÖNİZLEME\n\nHenüz dosya seçilmedi",
            fg="#77809a",
        )
        self.update_count()

    def load_queue(self) -> list[dict]:
        try:
            data = json.loads(self.data_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            changed = False
            for item in data:
                if (
                    item.get("type") == "Hikâye"
                    and item.get("status") != "Yayınlandı"
                ):
                    item["status"] = "Devre dışı"
                    item["error"] = (
                        "Instagram web arayüzü hikâye yayınlamayı desteklemiyor."
                    )
                    changed = True
            if changed:
                self.data_path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            return data
        except (OSError, ValueError, TypeError):
            return []

    def save_queue(self) -> None:
        self.data_path.write_text(
            json.dumps(self.queue, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def refresh_queue(self) -> None:
        self.queue_tree.delete(*self.queue_tree.get_children())
        self.waiting_count.set(
            str(sum(1 for item in self.queue if item.get("status") == "Bekliyor"))
        )
        self.published_count.set(
            str(sum(1 for item in self.queue if item.get("status") == "Yayınlandı"))
        )
        self.failed_count.set(
            str(sum(1 for item in self.queue if item.get("status") == "Başarısız"))
        )
        for item in sorted(self.queue, key=lambda row: row.get("publish_at", "")):
            try:
                stamp = datetime.fromisoformat(item["publish_at"]).strftime("%d.%m %H:%M")
            except (ValueError, KeyError):
                stamp = "Hatalı tarih"
            self.queue_tree.insert(
                "", "end", iid=item["id"],
                values=(item.get("type", ""), stamp, item.get("status", ""))
            )

    def delete_selected(self) -> None:
        selected = self.queue_tree.selection()
        if not selected:
            return
        self.queue = [item for item in self.queue if item.get("id") not in selected]
        self.save_queue()
        self.refresh_queue()

    def load_selected_to_editor(self) -> None:
        selected = self.queue_tree.selection()
        if not selected:
            messagebox.showinfo("Yayın seç", "Önce kuyruktan bir yayın seç.")
            return
        item = next(
            (row for row in self.queue if row.get("id") == selected[0]), None
        )
        if not item:
            return
        if item.get("type") == "Hikâye":
            messagebox.showinfo(
                "Hikâye devre dışı",
                "Hikâye paylaşımı Instagram web kısıtlaması nedeniyle editöre alınamaz.",
            )
            return
        self.content_type.set(item.get("type", "Gönderi"))
        media = item.get("media", "")
        self.selected_file.set(media)
        self.caption.delete("1.0", "end")
        self.caption.insert("1.0", item.get("caption", ""))
        try:
            publish_at = datetime.fromisoformat(item.get("publish_at", ""))
            if publish_at <= datetime.now():
                publish_at = datetime.now() + timedelta(minutes=5)
            self.publish_date.set(publish_at.strftime("%d.%m.%Y"))
            self.publish_time.set(publish_at.strftime("%H:%M"))
        except ValueError:
            self.quick_time(5)
        if media and Path(media).is_file():
            self.show_preview(media)
        self.update_count()
        self.status.set("Seçilen yayın editöre kopyalandı; kuyruktaki aslı korundu.")

    def retry_failed(self) -> None:
        for item in self.queue:
            if (
                item.get("status") == "Başarısız"
                and item.get("type") != "Hikâye"
            ):
                item["status"] = "Bekliyor"
                item["publish_at"] = datetime.now().isoformat(timespec="minutes")
                item["error"] = ""
        self.save_queue()
        self.refresh_queue()

    def scheduler_tick(self) -> None:
        if not self.closed and self.root.winfo_exists():
            if not self.running:
                now = datetime.now()
                due = next(
                    (
                        item for item in self.queue
                        if item.get("status") == "Bekliyor"
                        and self.parse_time(item.get("publish_at")) <= now
                    ),
                    None,
                )
                if due:
                    self.start_publish(due)
            self.root.after(1000, self.scheduler_tick)

    @staticmethod
    def parse_time(value) -> datetime:
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return datetime.max

    def browser_options(self, mobile: bool = False) -> Options:
        options = Options()
        if mobile:
            options.add_experimental_option(
                "mobileEmulation",
                {
                    "deviceMetrics": {
                        "width": 412,
                        "height": 915,
                        "pixelRatio": 2.625,
                        "touch": True,
                    },
                    "userAgent": (
                        "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/150.0.0.0 Mobile Safari/537.36"
                    ),
                },
            )
            options.add_argument("--window-size=760,980")
        else:
            options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        profile = uygulama_veri_klasoru() / "ChromeProfile"
        profile.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile}")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        return options

    def ensure_browser(self) -> Chrome:
        if self.browser:
            try:
                if self.browser.window_handles:
                    self.browser.switch_to.window(self.browser.window_handles[-1])
                    return self.browser
            except WebDriverException:
                self.browser = None
        self.browser = Chrome(options=self.browser_options())
        return self.browser

    def ensure_story_browser(self) -> Chrome:
        """Hikâye yükleme alanını sunan mobil Instagram görünümünü aç."""
        if self.browser is not None:
            try:
                self.browser.quit()
            except WebDriverException:
                pass
            self.browser = None
        self.browser = Chrome(options=self.browser_options(mobile=True))
        return self.browser

    @staticmethod
    def rotate_story_browser_landscape(browser: Chrome) -> None:
        """Dosya seçiminden sonra hikâye editörünü yatay mobil ölçüye geçir."""
        browser.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": 915,
                "height": 412,
                "deviceScaleFactor": 2.625,
                "mobile": True,
                "screenWidth": 915,
                "screenHeight": 412,
                "screenOrientation": {
                    "type": "landscapePrimary",
                    "angle": 90,
                },
            },
        )

    @staticmethod
    def prepare_story_landscape_navigation(browser: Chrome) -> None:
        """Mevcut dikey inputu bozmadan bir sonraki sayfaya yatay cihaz bilgisi ver."""
        browser.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    (() => {
                        const define = (object, name, getter) => {
                            try {
                                Object.defineProperty(object, name, {
                                    configurable: true,
                                    get: getter
                                });
                            } catch (_) {}
                        };
                        define(window, "innerWidth", () => 915);
                        define(window, "innerHeight", () => 412);
                        define(window.screen, "width", () => 915);
                        define(window.screen, "height", () => 412);
                        define(window.screen, "availWidth", () => 915);
                        define(window.screen, "availHeight", () => 412);
                        define(window.screen, "orientation", () => ({
                            type: "landscape-primary",
                            angle: 90,
                            onchange: null,
                            addEventListener() {},
                            removeEventListener() {}
                        }));
                        const originalMatchMedia = window.matchMedia.bind(window);
                        window.matchMedia = query => {
                            if (query.includes("orientation: landscape")) {
                                return {
                                    matches: true, media: query, onchange: null,
                                    addListener() {}, removeListener() {},
                                    addEventListener() {}, removeEventListener() {},
                                    dispatchEvent() { return true; }
                                };
                            }
                            if (query.includes("orientation: portrait")) {
                                return {
                                    matches: false, media: query, onchange: null,
                                    addListener() {}, removeListener() {},
                                    addEventListener() {}, removeEventListener() {},
                                    dispatchEvent() { return true; }
                                };
                            }
                            return originalMatchMedia(query);
                        };
                    })();
                """
            },
        )

    def open_chrome(self) -> None:
        def worker() -> None:
            try:
                browser = self.ensure_browser()
                browser.get("https://www.instagram.com/")
                self.root.after(0, lambda: self.status.set(
                    "Chrome açıldı • Gerekirse Instagram hesabına giriş yap."
                ))
            except Exception as exc:
                error_text = str(exc)
                self.root.after(
                    0,
                    lambda text=error_text: messagebox.showerror("Chrome açılamadı", text),
                )
        threading.Thread(target=worker, daemon=True).start()

    def start_publish(self, item: dict) -> None:
        if self.running:
            return
        self.running = True
        item["status"] = "Yayınlanıyor"
        self.save_queue()
        self.refresh_queue()
        self.progress.start(12)
        self.status.set(f"{item['type']} Instagram'a gönderiliyor…")
        threading.Thread(target=self.publish_worker, args=(item,), daemon=True).start()

    def publish_worker(self, item: dict) -> None:
        stage = "Chrome hazırlanıyor"
        try:
            browser = (
                self.ensure_story_browser()
                if item["type"] == "Hikâye"
                else self.ensure_browser()
            )
            stage = "Instagram açılıyor"
            self.update_publish_stage(stage)
            browser.get("https://www.instagram.com/")
            WebDriverWait(browser, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            if "accounts/login" in browser.current_url:
                raise RuntimeError(
                    "Instagram oturumu açık değil. Chrome'u Aç düğmesiyle giriş yapıp tekrar dene."
                )
            if item["type"] == "Hikâye":
                self.publish_story(browser, item, lambda value: self._stage(value))
            else:
                self.publish_post(browser, item, lambda value: self._stage(value))
            item["status"] = "Yayınlandı"
            item["error"] = ""
            message = f"{item['type']} başarıyla yayınlandı."
        except Exception as exc:
            stage = getattr(self, "_publish_stage", stage)
            diagnostic = self.save_publish_diagnostic(item, stage, exc)
            item["status"] = "Başarısız"
            detail = str(exc).split("Stacktrace:", 1)[0].strip()
            if isinstance(exc, TimeoutException):
                detail = "Instagram bu adımda beklenen ekran öğesini göstermedi."
            elif "only supports characters in the BMP" in detail:
                detail = "Açıklamadaki Unicode karakterler tarayıcıya aktarılamadı."
            item["error"] = f"{stage}: {detail or type(exc).__name__}"
            message = (
                f"Yayın başarısız • Aşama: {stage}\n"
                f"{detail or type(exc).__name__}\n"
                f"Tanılama: {diagnostic}"
            )
        self.save_queue()
        if item["type"] == "Hikâye" and self.browser is not None:
            try:
                self.browser.quit()
            except WebDriverException:
                pass
            self.browser = None
        self.root.after(0, lambda text=message: self.finish_publish(text))

    def _stage(self, value: str) -> None:
        self._publish_stage = value
        self.update_publish_stage(value)

    def update_publish_stage(self, stage: str) -> None:
        self.root.after(
            0, lambda value=stage: self.status.set(f"Yayın hazırlanıyor • {value}")
        )

    def save_publish_diagnostic(self, item: dict, stage: str, exc: Exception) -> str:
        folder = uygulama_veri_klasoru() / "tanilama" / "yayin"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = folder / f"yayin_{stamp}.json"
        try:
            current_url = self.browser.current_url if self.browser else ""
            parsed_url = urlparse(current_url)
            safe_url = (
                f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                if parsed_url.scheme and parsed_url.netloc
                else ""
            )
            report.write_text(
                json.dumps(
                    {
                        "time": datetime.now().isoformat(timespec="seconds"),
                        "version": self.VERSION,
                        "stage": stage,
                        "url": safe_url,
                        "media": Path(str(item.get("media", ""))).name,
                        "exception_type": type(exc).__name__,
                        "message": guvenli_hata_metni(exc),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            return str(report)
        except Exception:
            return str(folder)

    @staticmethod
    def click_text(browser: Chrome, texts: tuple[str, ...], timeout=20) -> None:
        conditions = " or ".join(
            f"normalize-space()={json.dumps(text)}" for text in texts
        )
        element = WebDriverWait(browser, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//*[self::button or self::div or self::span][{conditions}]")
            )
        )
        browser.execute_script("arguments[0].click();", element)

    def upload_file(self, browser: Chrome, media: str, timeout=20) -> None:
        upload = WebDriverWait(browser, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        upload.send_keys(str(Path(media).resolve()))

    @staticmethod
    def click_first(browser: Chrome, locators: list[tuple[str, str]], timeout=30) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for by, selector in locators:
                try:
                    elements = browser.find_elements(by, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            browser.execute_script("arguments[0].click();", element)
                            return
                except (StaleElementReferenceException, WebDriverException):
                    continue
            time.sleep(0.4)
        raise TimeoutException("Beklenen Instagram düğmesi bulunamadı.")

    def publish_post(self, browser: Chrome, item: dict, stage) -> None:
        stage("Gönderi oluşturma ekranı açılıyor")
        browser.get("https://www.instagram.com/create/select/")
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        if "accounts/login" in browser.current_url:
            raise RuntimeError("Instagram oturumu kapalı.")
        stage("Medya dosyası yükleniyor")
        self.upload_file(browser, item["media"], 20)
        next_buttons = [
            (By.XPATH, "//div[@role='button'][normalize-space()='İleri' or normalize-space()='Next']"),
            (By.XPATH, "//button[normalize-space()='İleri' or normalize-space()='Next']"),
            (By.XPATH, "//*[normalize-space()='İleri' or normalize-space()='Next']/ancestor::*[@role='button'][1]"),
        ]
        stage("Görsel düzenleme adımı geçiliyor")
        self.click_first(browser, next_buttons, 30)
        stage("Filtre adımı geçiliyor")
        self.click_first(browser, next_buttons, 30)
        caption = item.get("caption", "")
        if caption:
            stage("Açıklama yazılıyor")
            area = WebDriverWait(browser, 25).until(
                lambda driver: next(
                    (
                        element
                        for selector in (
                            "div[aria-label='Bir açıklama yaz...'][contenteditable='true']",
                            "div[aria-label='Write a caption...'][contenteditable='true']",
                            "div[contenteditable='true'][role='textbox']",
                            "textarea[aria-label*='açıklama']",
                            "textarea[aria-label*='caption']",
                        )
                        for element in driver.find_elements(By.CSS_SELECTOR, selector)
                        if element.is_displayed()
                    ),
                    False,
                )
            )
            area.click()
            self.set_unicode_text(browser, area, caption)
        stage("Paylaş düğmesine basılıyor")
        self.click_first(
            browser,
            [
                (By.XPATH, "//div[@role='button'][normalize-space()='Paylaş' or normalize-space()='Share']"),
                (By.XPATH, "//button[normalize-space()='Paylaş' or normalize-space()='Share']"),
                (By.XPATH, "//*[normalize-space()='Paylaş' or normalize-space()='Share']/ancestor::*[@role='button'][1]"),
            ],
            30,
        )
        stage("Instagram yayın sonucunu doğruluyor")
        WebDriverWait(browser, 90).until(
            lambda driver: (
                "/create/" not in driver.current_url
                or any(
                    phrase in driver.page_source
                    for phrase in (
                        "Gönderin paylaşıldı",
                        "Your post has been shared",
                        "Post shared",
                    )
                )
            )
        )

    @staticmethod
    def set_unicode_text(browser: Chrome, element, text: str) -> None:
        """Emoji dahil tüm Unicode metni React kontrollü alana güvenle yerleştir."""
        browser.execute_script(
            """
            const element = arguments[0];
            const value = arguments[1];
            element.focus();

            if (element.tagName === "TEXTAREA" || element.tagName === "INPUT") {
                const prototype = element.tagName === "TEXTAREA"
                    ? window.HTMLTextAreaElement.prototype
                    : window.HTMLInputElement.prototype;
                const setter = Object.getOwnPropertyDescriptor(prototype, "value").set;
                setter.call(element, value);
            } else {
                element.textContent = value;
            }

            element.dispatchEvent(new InputEvent("input", {
                bubbles: true,
                inputType: "insertText",
                data: value
            }));
            element.dispatchEvent(new Event("change", {bubbles: true}));
            element.dispatchEvent(new Event("blur", {bubbles: true}));
            """,
            element,
            text,
        )
        inserted = browser.execute_script(
            """
            const element = arguments[0];
            return element.value !== undefined ? element.value : element.textContent;
            """,
            element,
        )
        if inserted != text:
            raise RuntimeError("Açıklama Instagram alanına eksiksiz aktarılamadı.")

    def publish_story(self, browser: Chrome, item: dict, stage) -> None:
        stage("Mobil hikâye yükleme ekranı hazırlanıyor")
        browser.get("https://www.instagram.com/")
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        for text in ("Şimdi değil", "Not now"):
            try:
                button = WebDriverWait(browser, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//*[normalize-space()={json.dumps(text)}]")
                    )
                )
                browser.execute_script("arguments[0].click();", button)
                time.sleep(1)
                break
            except TimeoutException:
                continue
        stage("Hikâye medyası yükleniyor")
        inputs = WebDriverWait(browser, 25).until(
            lambda driver: driver.find_elements(
                By.CSS_SELECTOR, "input[type='file'][accept*='image']"
            )
        )
        upload = next(
            (
                element
                for element in inputs
                if "png" in (element.get_attribute("accept") or "").casefold()
            ),
            inputs[0],
        )
        stage("Hikâye sayfasına yatay cihaz bilgisi hazırlanıyor")
        self.prepare_story_landscape_navigation(browser)
        upload.send_keys(str(Path(item["media"]).resolve()))
        WebDriverWait(browser, 25).until(
            lambda driver: "/create/story" in driver.current_url.casefold()
        )
        stage("Hikâye düzenleme ekranı bekleniyor")
        self.click_first(
            browser,
            [
                (
                    By.XPATH,
                    "//*[normalize-space()='Hikayene ekle' "
                    "or normalize-space()='Hikâyene ekle' "
                    "or normalize-space()='Hikayende paylaş' "
                    "or normalize-space()='Hikâyende paylaş' "
                    "or normalize-space()='Add to story' "
                    "or normalize-space()='Share to story']",
                ),
            ],
            45,
        )
        stage("Instagram hikâye sonucunu doğruluyor")
        WebDriverWait(browser, 60).until(
            lambda driver: not any(
                element.is_displayed()
                for element in driver.find_elements(
                    By.XPATH,
                    "//*[normalize-space()='Hikayene ekle' "
                    "or normalize-space()='Hikâyene ekle' "
                    "or normalize-space()='Hikayende paylaş' "
                    "or normalize-space()='Hikâyende paylaş' "
                    "or normalize-space()='Add to story' "
                    "or normalize-space()='Share to story']",
                )
            )
        )

    def finish_publish(self, message: str) -> None:
        self.running = False
        self.progress.stop()
        self.status.set(message)
        self.refresh_queue()
        if message.startswith("Yayın başarısız"):
            messagebox.showerror("Instagram yayını tamamlanamadı", message)

    def back_to_menu(self) -> None:
        if self.running:
            messagebox.showwarning("Yayın sürüyor", "Yayın bitmeden ana menüye dönemezsin.")
            return
        if self.browser:
            try:
                self.browser.quit()
            except WebDriverException:
                pass
        self.closed = True
        self.release_scroll_binding()
        BaslangicMenusu(self.root)

    def close(self) -> None:
        self.closed = True
        self.release_scroll_binding()
        self.save_queue()
        if self.browser:
            try:
                self.browser.quit()
            except WebDriverException:
                pass
        self.root.destroy()


_INSTANCE_MUTEX = None


def ensure_single_instance(root: tk.Tk) -> bool:
    """Aynı veri/Chrome profilini kullanan ikinci uygulama örneğini engeller."""
    global _INSTANCE_MUTEX
    if os.name != "nt":
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    mutex = kernel32.CreateMutexW(
        None, False, "Local\\BurakHocaInstagramPaneli_SingleInstance_v3"
    )
    if not mutex:
        return True
    _INSTANCE_MUTEX = mutex
    if ctypes.get_last_error() == 183:
        messagebox.showwarning(
            "Uygulama zaten açık",
            "Instagram Paneli zaten çalışıyor. Aynı Chrome profilinin bozulmaması için "
            "ikinci pencere açılmadı.",
            parent=root,
        )
        return False
    return True


if __name__ == "__main__":
    window = tk.Tk()
    window.withdraw()
    if ensure_single_instance(window):
        window.deiconify()
        BaslangicMenusu(window)
        window.mainloop()
    else:
        window.destroy()
