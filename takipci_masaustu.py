"""Instagram takipçi listesini işleyen masaüstü uygulaması."""

from __future__ import annotations

import csv
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
from urllib.parse import urlparse

import pystray
from PIL import Image, ImageDraw
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


class TakipciUygulamasi:
    VERSION = "2.4.0"

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
                f"{type(exc).__name__}: {exc}", encoding="utf-8"
            )
            if self.browser is not None:
                self.browser.save_screenshot(
                    str(self.diagnostics_dir / f"ekran_{stamp}.png")
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


if __name__ == "__main__":
    window = tk.Tk()
    TakipciUygulamasi(window)
    window.mainloop()
