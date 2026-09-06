import json
import os
import re
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk


APP_NAME = "桌面备忘录"
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
DATA_FILE = Path(os.environ.get("APPDATA", Path.home())) / "DesktopMemo" / "notes.json"
LOCAL_DATA_FILE = APP_DIR / "notes.json"
SETTINGS_FILE = DATA_FILE.parent / "settings.json"
LOCAL_SETTINGS_FILE = APP_DIR / "settings.json"
ICON_PNG = RESOURCE_DIR / "desktop-memo-icon.png"
ICON_ICO = RESOURCE_DIR / "desktop-memo-icon.ico"

BG = "#E6E1DB"
SURFACE = "#F1EEE9"
SURFACE_ALT = "#DEDCD7"
TEXT = "#4B5054"
MUTED = "#777C7D"
SAGE = "#A8B2A0"
SAGE_DARK = "#87958A"
SLATE = "#9AAAB3"
TERRACOTTA = "#C28F7C"
CREAM = "#F6F1E8"
BORDER = "#C9C6BF"


class DesktopMemo(tk.Tk):
    def __init__(self, widget_only=False):
        super().__init__()
        self.widget_only = widget_only
        self.title(APP_NAME)
        self.geometry("450x580")
        self.minsize(380, 420)
        self.configure(bg=BG)
        self.notes = []
        self.current_index = None
        self.search_var = tk.StringVar()
        self.pin_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="准备好了")
        self._autosave_job = None
        self.widget_window = None
        self.widget_drag_offset = (0, 0)
        self.saved_widget_geometry = None
        self.saved_splitter_pos = None

        self._load_window_state()
        self._setup_style()
        self._set_icon()
        if self.widget_only:
            self.withdraw()
        else:
            self._build_ui()
        self._load_notes()
        if not self.widget_only:
            self._bind_events()
        self._create_desktop_widget()
        self._update_widget()
        if self.widget_only:
            self._watch_notes_file()

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background=BG)
        style.configure("Card.TFrame", background=SURFACE)
        style.configure("Title.TLabel", background=SURFACE, foreground=TEXT, font=("Microsoft YaHei UI", 16, "bold"))
        style.configure("Muted.TLabel", background=SURFACE, foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("Footer.TLabel", background=BG, foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("Toolbar.TButton", background=SURFACE_ALT, foreground=TEXT, bordercolor=BORDER, lightcolor=SURFACE_ALT, darkcolor=BORDER, padding=(10, 5), font=("Microsoft YaHei UI", 9))
        style.map("Toolbar.TButton", background=[("active", SAGE), ("pressed", SAGE_DARK)], foreground=[("pressed", "#FFFFFF")])
        style.configure("Accent.TButton", background=SLATE, foreground="#FFFFFF", bordercolor=SLATE, lightcolor=SLATE, darkcolor=SAGE_DARK, padding=(11, 5), font=("Microsoft YaHei UI", 9, "bold"))
        style.map("Accent.TButton", background=[("active", TERRACOTTA), ("pressed", SAGE_DARK)])
        style.configure("TEntry", fieldbackground=CREAM, foreground=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        style.configure("TCheckbutton", background=SURFACE, foreground=TEXT, font=("Microsoft YaHei UI", 9))
        style.map("TCheckbutton", background=[("active", SURFACE)], foreground=[("active", SAGE_DARK)])
        style.configure("TScrollbar", troughcolor=SURFACE_ALT, background=SLATE, arrowcolor=TEXT, bordercolor=SURFACE_ALT)

    def _set_icon(self):
        try:
            if ICON_ICO.exists():
                self.iconbitmap(str(ICON_ICO))
            if ICON_PNG.exists():
                self._icon_image = tk.PhotoImage(file=str(ICON_PNG))
                self.iconphoto(True, self._icon_image)
        except tk.TclError:
            pass

    def _setup_preview_tags(self):
        self.preview_text.tag_configure("h1", font=("Microsoft YaHei UI", 16, "bold"), foreground=SAGE_DARK, spacing1=8, spacing3=5)
        self.preview_text.tag_configure("h2", font=("Microsoft YaHei UI", 13, "bold"), foreground=SLATE, spacing1=6, spacing3=4)
        self.preview_text.tag_configure("h3", font=("Microsoft YaHei UI", 11, "bold"), foreground=TERRACOTTA, spacing1=5, spacing3=3)
        self.preview_text.tag_configure("bold", font=("Microsoft YaHei UI", 11, "bold"))
        self.preview_text.tag_configure("italic", font=("Microsoft YaHei UI", 11, "italic"), foreground=MUTED)
        self.preview_text.tag_configure("code", font=("Consolas", 10), foreground=SAGE_DARK, background="#E4E0D8")
        self.preview_text.tag_configure("codeblock", font=("Consolas", 10), foreground=TEXT, background="#E4E0D8", lmargin1=10, lmargin2=10)

    def _insert_inline_markdown(self, text):
        pattern = r"(\*\*.*?\*\*|`.*?`|\*.*?\*)"
        for part in re.split(pattern, text):
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                self.preview_text.insert("end", part[2:-2], "bold")
            elif part.startswith("`") and part.endswith("`"):
                self.preview_text.insert("end", part[1:-1], "code")
            elif part.startswith("*") and part.endswith("*"):
                self.preview_text.insert("end", part[1:-1], "italic")
            else:
                self.preview_text.insert("end", part)

    def _render_preview(self):
        if not hasattr(self, "preview_text"):
            return
        markdown = self.body_text.get("1.0", "end-1c")
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", tk.END)
        in_code_block = False
        for raw_line in markdown.splitlines():
            line = raw_line.rstrip()
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                if not in_code_block:
                    self.preview_text.insert("end", "\n")
                continue
            if in_code_block:
                self.preview_text.insert("end", line + "\n", "codeblock")
                continue
            heading = re.match(r"^(#{1,3})\s+(.+)$", line)
            if heading:
                self.preview_text.insert("end", heading.group(2) + "\n", f"h{len(heading.group(1))}")
            elif re.match(r"^\s*[-*]\s+", line):
                self.preview_text.insert("end", "• ")
                self._insert_inline_markdown(re.sub(r"^\s*[-*]\s+", "", line))
                self.preview_text.insert("end", "\n")
            else:
                self._insert_inline_markdown(line)
                self.preview_text.insert("end", "\n")
        self.preview_text.configure(state="disabled")

    def _on_body_changed(self):
        self._render_preview()
        self._schedule_autosave()

    def _build_ui(self):
        outer = ttk.Frame(self, style="App.TFrame", padding=14)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="Card.TFrame", padding=(16, 12))
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="桌面备忘录", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="自动保存到本机", style="Muted.TLabel").pack(side="left", padx=(12, 0), pady=(5, 0))
        ttk.Checkbutton(header, text="窗口置顶", variable=self.pin_var, command=self._toggle_topmost).pack(side="right")

        toolbar = ttk.Frame(outer, style="Card.TFrame", padding=(12, 10))
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Button(toolbar, text="＋ 新建", style="Accent.TButton", command=self.new_note).pack(side="left")
        ttk.Button(toolbar, text="保存", style="Toolbar.TButton", command=self.save_current).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="删除", style="Toolbar.TButton", command=self.delete_current).pack(side="left", padx=(8, 0))
        self.pin_button = ttk.Button(toolbar, text="置顶", style="Toolbar.TButton", command=self.toggle_pin)
        self.pin_button.pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="桌面小组件", style="Toolbar.TButton", command=self.toggle_widget).pack(side="left", padx=(8, 0))
        ttk.Label(toolbar, text="搜索：", style="Muted.TLabel").pack(side="left", padx=(24, 0))
        search = ttk.Entry(toolbar, textvariable=self.search_var, width=26)
        search.pack(side="left")
        ttk.Button(toolbar, text="清除", style="Toolbar.TButton", command=lambda: self.search_var.set("")).pack(side="left", padx=(6, 0))

        content = ttk.Frame(outer, style="App.TFrame")
        content.pack(fill="both", expand=True)
        content.rowconfigure(0, weight=1)

        list_card = ttk.Frame(content, style="Card.TFrame", padding=10)
        list_card.rowconfigure(1, weight=1)
        list_card.columnconfigure(0, weight=1)
        ttk.Label(list_card, text="便签列表", style="Muted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 7))
        list_frame = ttk.Frame(list_card, style="Card.TFrame")
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.note_list = tk.Listbox(
            list_frame,
            width=25,
            activestyle="none",
            exportselection=False,
            relief="flat",
            borderwidth=0,
            bg=SURFACE,
            fg=TEXT,
            selectbackground="#B8C4BE",
            selectforeground=TEXT,
            font=("Microsoft YaHei UI", 10),
            highlightthickness=0,
        )
        self.note_list.grid(row=0, column=0, sticky="nsew")
        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.note_list.yview)
        list_scroll.grid(row=0, column=1, sticky="ns")
        self.note_list.configure(yscrollcommand=list_scroll.set)

        editor_card = ttk.Frame(content, style="Card.TFrame", padding=14)
        editor_card.rowconfigure(3, weight=1)
        editor_card.columnconfigure(0, weight=1)
        ttk.Label(editor_card, text="编辑内容", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.title_entry = ttk.Entry(editor_card, font=("Microsoft YaHei UI", 12, "bold"))
        self.title_entry.grid(row=1, column=0, sticky="ew", pady=(8, 8))
        self.title_entry.insert(0, "新便签")
        ttk.Label(editor_card, text="支持 Markdown：# 标题   - 列表   **加粗**   `代码`   ```代码块```", style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 6))
        text_frame = ttk.Frame(editor_card, style="Card.TFrame")
        text_frame.grid(row=3, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        self.editor_tabs = ttk.Notebook(text_frame)
        self.editor_tabs.grid(row=0, column=0, columnspan=2, sticky="nsew")
        edit_tab = ttk.Frame(self.editor_tabs, style="Card.TFrame", padding=2)
        preview_tab = ttk.Frame(self.editor_tabs, style="Card.TFrame", padding=2)
        edit_tab.rowconfigure(0, weight=1)
        edit_tab.columnconfigure(0, weight=1)
        preview_tab.rowconfigure(0, weight=1)
        preview_tab.columnconfigure(0, weight=1)
        self.editor_tabs.add(edit_tab, text="编辑 Markdown")
        self.editor_tabs.add(preview_tab, text="预览")
        self.body_text = tk.Text(
            edit_tab,
            wrap="word",
            undo=True,
            relief="flat",
            borderwidth=0,
            bg=CREAM,
            fg=TEXT,
            insertbackground=TEXT,
            padx=12,
            pady=12,
            font=("Microsoft YaHei UI", 11),
            highlightthickness=1,
            highlightbackground="#D5CABB",
            highlightcolor=SLATE,
        )
        self.body_text.grid(row=0, column=0, sticky="nsew")
        text_scroll = ttk.Scrollbar(edit_tab, orient="vertical", command=self.body_text.yview)
        text_scroll.grid(row=0, column=1, sticky="ns")
        self.body_text.configure(yscrollcommand=text_scroll.set)
        self.preview_text = tk.Text(
            preview_tab,
            wrap="word",
            relief="flat",
            borderwidth=0,
            bg=CREAM,
            fg=TEXT,
            padx=14,
            pady=14,
            font=("Microsoft YaHei UI", 11),
            state="disabled",
            cursor="arrow",
        )
        self.preview_text.grid(row=0, column=0, sticky="nsew")
        preview_scroll = ttk.Scrollbar(preview_tab, orient="vertical", command=self.preview_text.yview)
        preview_scroll.grid(row=0, column=1, sticky="ns")
        self.preview_text.configure(yscrollcommand=preview_scroll.set)
        self._setup_preview_tags()

        self.splitter = ttk.Panedwindow(content, orient="horizontal")
        self.splitter.grid(row=0, column=0, sticky="nsew")
        self.splitter.add(list_card, weight=1)
        self.splitter.add(editor_card, weight=3)
        if self.saved_splitter_pos:
            self.after_idle(self._restore_splitter_position)

        footer = ttk.Frame(outer, style="App.TFrame")
        footer.pack(fill="x", pady=(8, 0))
        ttk.Label(footer, textvariable=self.status_var, style="Footer.TLabel").pack(side="left")
        ttk.Label(footer, text="Ctrl+N 新建   Ctrl+S 保存   Delete 删除当前便签", style="Footer.TLabel").pack(side="right")

        self._toggle_topmost()

    def _restore_splitter_position(self):
        try:
            self.splitter.sashpos(0, int(self.saved_splitter_pos))
        except (TypeError, tk.TclError):
            pass

    def _bind_events(self):
        self.note_list.bind("<<ListboxSelect>>", self._on_note_selected)
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        self.title_entry.bind("<KeyRelease>", lambda event: self._schedule_autosave())
        self.body_text.bind("<KeyRelease>", lambda event: self._on_body_changed())
        self.editor_tabs.bind("<<NotebookTabChanged>>", lambda _event: self._render_preview())
        self.bind("<Control-n>", lambda event: self.new_note())
        self.bind("<Control-s>", lambda event: self.save_current())
        self.bind("<Delete>", lambda event: self.delete_current())
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _load_notes(self):
        try:
            data_file = DATA_FILE if DATA_FILE.exists() else LOCAL_DATA_FILE
            if data_file.exists():
                self.notes = json.loads(data_file.read_text(encoding="utf-8"))
                if not isinstance(self.notes, list):
                    self.notes = []
                self.notes = [note for note in self.notes if isinstance(note, dict)]
                for note in self.notes:
                    note["pinned"] = bool(note.get("pinned", False))
        except (OSError, json.JSONDecodeError):
            self.notes = []
        if self.notes:
            self.current_index = self._ordered_indices()[0]
            if not self.widget_only:
                self._refresh_list()
                self._select_visible_index(0)
        elif not self.widget_only:
            self.new_note()

    def _watch_notes_file(self):
        if not self.widget_only:
            return
        try:
            data_file = DATA_FILE if DATA_FILE.exists() else LOCAL_DATA_FILE
            mtime = data_file.stat().st_mtime if data_file.exists() else None
            if getattr(self, "_notes_mtime", None) != mtime:
                self._notes_mtime = mtime
                if data_file.exists():
                    loaded = json.loads(data_file.read_text(encoding="utf-8"))
                    if isinstance(loaded, list):
                        self.notes = loaded
                        self.notes = [note for note in self.notes if isinstance(note, dict)]
                        for note in self.notes:
                            note["pinned"] = bool(note.get("pinned", False))
                        ordered = self._ordered_indices()
                        self.current_index = ordered[0] if ordered else None
                        self._update_widget()
        except (OSError, json.JSONDecodeError):
            pass
        self.after(1000, self._watch_notes_file)

    def _write_notes(self):
        content = json.dumps(self.notes, ensure_ascii=False, indent=2)
        try:
            DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            DATA_FILE.write_text(content, encoding="utf-8")
        except OSError:
            # Some restricted environments block AppData; keep the app usable
            # by storing the notes beside the portable launcher instead.
            LOCAL_DATA_FILE.write_text(content, encoding="utf-8")

    def _load_window_state(self):
        try:
            settings_file = SETTINGS_FILE if SETTINGS_FILE.exists() else LOCAL_SETTINGS_FILE
            if settings_file.exists():
                settings = json.loads(settings_file.read_text(encoding="utf-8"))
                geometry = settings.get("geometry")
                if isinstance(geometry, str) and geometry:
                    self.geometry(geometry)
                self.pin_var.set(bool(settings.get("topmost", True)))
                self.saved_widget_geometry = settings.get("widget_geometry")
                self.saved_splitter_pos = settings.get("splitter_pos")
        except (OSError, json.JSONDecodeError, tk.TclError):
            pass

    def _save_window_state(self):
        widget_geometry = self.saved_widget_geometry
        if self.widget_window is not None:
            widget_geometry = self.widget_window.geometry()
        splitter_pos = self.saved_splitter_pos
        if hasattr(self, "splitter"):
            try:
                splitter_pos = self.splitter.sashpos(0)
            except tk.TclError:
                pass
        content = json.dumps(
            {
                "geometry": self.geometry(),
                "topmost": self.pin_var.get(),
                "widget_geometry": widget_geometry,
                "splitter_pos": splitter_pos,
            },
            ensure_ascii=False,
            indent=2,
        )
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(content, encoding="utf-8")
        except OSError:
            try:
                LOCAL_SETTINGS_FILE.write_text(content, encoding="utf-8")
            except OSError:
                pass

    def _create_desktop_widget(self):
        self.widget_window = tk.Toplevel(self)
        self.widget_window.title("桌面便签")
        self.widget_window.geometry(self.saved_widget_geometry or "300x280")
        self.widget_window.resizable(False, False)
        self.widget_window.overrideredirect(True)
        self.widget_window.attributes("-topmost", True)
        self.widget_window.configure(bg=BORDER)

        shell = tk.Frame(self.widget_window, bg=SURFACE, highlightthickness=1, highlightbackground=BORDER)
        shell.pack(fill="both", expand=True, padx=1, pady=1)

        header = tk.Frame(shell, bg=SAGE_DARK, height=42)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.widget_header = tk.Label(header, text="桌面便签", bg=SAGE_DARK, fg="#FFFFFF", anchor="w", padx=14, font=("Microsoft YaHei UI", 10, "bold"))
        self.widget_header.pack(side="left", fill="both", expand=True)
        close_button = tk.Button(header, text="×", command=self._hide_widget, bg=SAGE_DARK, fg="#FFFFFF", activebackground=TERRACOTTA, activeforeground="#FFFFFF", relief="flat", bd=0, font=("Segoe UI", 16), width=3, cursor="hand2")
        close_button.pack(side="right", fill="y")

        card = tk.Frame(shell, bg=CREAM, padx=16, pady=14)
        card.pack(fill="both", expand=True)
        self.widget_title = tk.Label(card, text="暂无便签", bg=CREAM, fg=TEXT, anchor="w", justify="left", wraplength=258, font=("Microsoft YaHei UI", 13, "bold"))
        self.widget_title.pack(fill="x", pady=(0, 10))
        self.widget_body = tk.Label(card, text="点击“＋ 新建”开始记录", bg=CREAM, fg=TEXT, anchor="nw", justify="left", wraplength=258, font=("Microsoft YaHei UI", 10), height=7)
        self.widget_body.pack(fill="both", expand=True)
        self.widget_footer = tk.Label(card, text="", bg=CREAM, fg=MUTED, anchor="w", font=("Microsoft YaHei UI", 8))
        self.widget_footer.pack(fill="x", pady=(8, 8))
        open_button = tk.Button(card, text="打开编辑", command=self._show_main_window, bg=SLATE, fg="#FFFFFF", activebackground=TERRACOTTA, activeforeground="#FFFFFF", relief="flat", bd=0, padx=12, pady=5, cursor="hand2", font=("Microsoft YaHei UI", 9, "bold"))
        open_button.pack(anchor="e")

        for target in (header, self.widget_header, card, self.widget_title, self.widget_body, self.widget_footer):
            target.bind("<ButtonPress-1>", self._widget_drag_start)
            target.bind("<B1-Motion>", self._widget_drag_move)
            target.bind("<ButtonRelease-1>", lambda _event: self._save_window_state())
        for target in (self.widget_title, self.widget_body):
            target.bind("<Double-Button-1>", lambda _event: self._show_main_window())

        self._place_widget()

    def _place_widget(self):
        if self.widget_window is None:
            return
        if self.saved_widget_geometry:
            self.widget_window.geometry(self.saved_widget_geometry)
            return
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        self.widget_window.geometry(f"300x280+{max(0, screen_width - 330)}+100")

    def _widget_drag_start(self, event):
        if self.widget_window is None:
            return
        self.widget_drag_offset = (event.x_root - self.widget_window.winfo_x(), event.y_root - self.widget_window.winfo_y())

    def _widget_drag_move(self, event):
        if self.widget_window is None:
            return
        x = event.x_root - self.widget_drag_offset[0]
        y = event.y_root - self.widget_drag_offset[1]
        self.widget_window.geometry(f"300x280+{x}+{y}")

    def _hide_widget(self):
        if self.widget_window is not None:
            if self.widget_only:
                self._close()
                return
            self.saved_widget_geometry = self.widget_window.geometry()
            self.widget_window.withdraw()
            self._save_window_state()

    def toggle_widget(self):
        if self.widget_window is None:
            self._create_desktop_widget()
            self._update_widget()
        elif self.widget_window.state() == "withdrawn":
            self._place_widget()
            self.widget_window.deiconify()
            self.widget_window.lift()
        else:
            self._hide_widget()

    def _show_main_window(self):
        if self.widget_only:
            if getattr(sys, "frozen", False):
                subprocess.Popen([sys.executable], cwd=str(APP_DIR))
            else:
                script_path = Path(__file__).with_name("DesktopMemo.py")
                subprocess.Popen([sys.executable, str(script_path)], cwd=str(script_path.parent))
            return
        self.deiconify()
        self.lift()
        self.focus_force()

    def _update_widget(self):
        if self.widget_window is None:
            return
        if self.current_index is None or self.current_index >= len(self.notes):
            self.widget_header.configure(text="桌面便签")
            self.widget_title.configure(text="暂无便签")
            self.widget_body.configure(text="点击“＋ 新建”开始记录")
            self.widget_footer.configure(text="")
            return
        note = self.notes[self.current_index]
        title = note.get("title", "未命名便签") or "未命名便签"
        body = note.get("body", "").strip() or "（这条便签还没有内容）"
        if len(body) > 180:
            body = body[:180].rstrip() + "…"
        self.widget_title.configure(text=title)
        self.widget_body.configure(text=body)
        self.widget_footer.configure(text=f"更新于 {note.get('updated_at', '')}")
        self.widget_header.configure(text="📌 桌面便签" if note.get("pinned", False) else "桌面便签")

    def _update_pin_button(self):
        if not hasattr(self, "pin_button"):
            return
        is_pinned = self.current_index is not None and self.current_index < len(self.notes) and self.notes[self.current_index].get("pinned", False)
        self.pin_button.configure(text="取消置顶" if is_pinned else "置顶")

    def toggle_pin(self):
        if self.current_index is None or self.current_index >= len(self.notes):
            return
        note = self.notes[self.current_index]
        note["pinned"] = not note.get("pinned", False)
        self._write_notes()
        self._refresh_list()
        visible = self._visible_indices()
        if self.current_index in visible:
            selected = visible.index(self.current_index)
            self.note_list.selection_set(selected)
            self.note_list.see(selected)
        self._update_pin_button()
        self._update_widget()

    def _refresh_list(self):
        keyword = self.search_var.get().strip().lower()
        self.note_list.delete(0, tk.END)
        for index in self._visible_indices():
            note = self.notes[index]
            title = note.get("title", "未命名便签") or "未命名便签"
            body = note.get("body", "").replace("\n", " ").strip()
            pin_mark = "📌 " if note.get("pinned", False) else ""
            preview = f"{pin_mark}{title}  ·  {body[:18]}" if body else f"{pin_mark}{title}"
            self.note_list.insert(tk.END, preview)

    def _visible_indices(self):
        keyword = self.search_var.get().strip().lower()
        return [
            index for index in self._ordered_indices()
            for note in [self.notes[index]]
            if not keyword or keyword in f"{note.get('title', '')} {note.get('body', '')}".lower()
        ]

    def _ordered_indices(self):
        return sorted(
            range(len(self.notes)),
            key=lambda index: not bool(self.notes[index].get("pinned", False)),
        )

    def _select_visible_index(self, visible_index):
        visible = self._visible_indices()
        if not visible:
            self.current_index = None
            self._clear_editor()
            return
        visible_index = max(0, min(visible_index, len(visible) - 1))
        self.note_list.selection_clear(0, tk.END)
        self.note_list.selection_set(visible_index)
        self.note_list.see(visible_index)
        self.current_index = visible[visible_index]
        self._load_current_into_editor()

    def _on_note_selected(self, _event=None):
        selected = self.note_list.curselection()
        if not selected:
            return
        visible = self._visible_indices()
        if selected[0] < len(visible):
            self.current_index = visible[selected[0]]
            self._load_current_into_editor()

    def _load_current_into_editor(self):
        if self.current_index is None or self.current_index >= len(self.notes):
            return
        note = self.notes[self.current_index]
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, note.get("title", "未命名便签"))
        self.body_text.delete("1.0", tk.END)
        self.body_text.insert("1.0", note.get("body", ""))
        self.status_var.set(f"上次保存：{note.get('updated_at', '刚刚')}")
        self._render_preview()
        self._update_pin_button()
        self._update_widget()

    def _clear_editor(self):
        self.title_entry.delete(0, tk.END)
        self.body_text.delete("1.0", tk.END)
        self.status_var.set("没有匹配的便签")
        self._render_preview()
        self._update_pin_button()
        self._update_widget()

    def _schedule_autosave(self):
        if self.current_index is None:
            return
        if self._autosave_job:
            self.after_cancel(self._autosave_job)
        self.status_var.set("正在编辑，稍后自动保存…")
        self._autosave_job = self.after(800, self.save_current)

    def new_note(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.notes.insert(0, {"title": "新便签", "body": "", "updated_at": now, "pinned": False})
        self.search_var.set("")
        self._write_notes()
        self._refresh_list()
        self._select_visible_index(0)
        self.title_entry.focus_set()
        self.title_entry.selection_range(0, tk.END)
        self.status_var.set("已新建便签")

    def save_current(self):
        if self.current_index is None or self.current_index >= len(self.notes):
            return
        title = self.title_entry.get().strip() or "未命名便签"
        body = self.body_text.get("1.0", "end-1c").strip()
        self.notes[self.current_index] = {
            "title": title,
            "body": body,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "pinned": self.notes[self.current_index].get("pinned", False),
        }
        self._write_notes()
        self._refresh_list()
        visible = self._visible_indices()
        if self.current_index in visible:
            selected = visible.index(self.current_index)
            self.note_list.selection_set(selected)
            self.note_list.see(selected)
        self.status_var.set("已自动保存 · " + datetime.now().strftime("%H:%M:%S"))
        self._update_pin_button()
        self._update_widget()
        self._autosave_job = None

    def delete_current(self):
        if self.current_index is None or self.current_index >= len(self.notes):
            return
        title = self.notes[self.current_index].get("title", "未命名便签")
        if not messagebox.askyesno("删除便签", f"确定删除“{title}”吗？"):
            return
        deleted_index = self.current_index
        self.notes.pop(deleted_index)
        self._write_notes()
        self._refresh_list()
        visible = self._visible_indices()
        if visible:
            next_index = min(deleted_index, len(visible) - 1)
            self._select_visible_index(next_index)
        else:
            self.current_index = None
            self._clear_editor()
        self.status_var.set("便签已删除")

    def _toggle_topmost(self):
        self.attributes("-topmost", self.pin_var.get())

    def _close(self):
        if not self.widget_only:
            self.save_current()
        self._save_window_state()
        if self.widget_window is not None:
            self.widget_window.destroy()
        self.destroy()


if __name__ == "__main__":
    app = DesktopMemo(widget_only="--widget-only" in sys.argv)
    app.mainloop()
