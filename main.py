import os
import sys
import time
import queue
import threading
import subprocess
from pathlib import Path
from collections import defaultdict
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont

# macOS: System Python (3.9.6) includes obsolete Tk 8.5 which renders a blank window on modern macOS.
# Automatically upgrade process to modern Homebrew Python (Tk 8.6+/9.0+) if available.
if sys.platform == "darwin":
    try:
        import tkinter as _tk
        if _tk.TkVersion < 8.6:
            for _candidate in ["/opt/homebrew/bin/python3", "/usr/local/bin/python3"]:
                if os.path.exists(_candidate) and sys.executable != _candidate:
                    _args = sys.argv.copy()
                    if not _args or _args[0] in ("-c", ""):
                        _args = [__file__] + _args[1:]
                    os.execv(_candidate, [_candidate] + _args)
    except Exception:
        pass

# Silence macOS Tk deprecation notice
os.environ["TK_SILENCE_DEPRECATION"] = "1"

try:
    import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

from scanner import scan_folder
from organizer import organize_files, get_category, CATEGORY_MAP, CATEGORY_COLORS
from duplicate_finder import find_duplicates
from report import generate_report, format_size
from demo_test_files import create_demo_data

# ============================================================================
# DESIGN SYSTEM & THEME TOKENS
# ============================================================================

THEMES = {
    "dark": {
        "bg": "#0a0e17",
        "card": "#131b2e",
        "card_hover": "#1c2640",
        "surface": "#162035",
        "surface_hover": "#222f4c",
        "border": "#212d45",
        "border_focus": "#6366f1",
        "text": "#f8fafc",
        "text_secondary": "#94a3b8",
        "text_muted": "#64748b",
        "accent": "#6366f1",
        "accent_hover": "#4f46e5",
        "accent_text": "#ffffff",
        "success": "#10b981",
        "success_hover": "#059669",
        "warning": "#f59e0b",
        "warning_hover": "#d97706",
        "danger": "#ef4444",
        "danger_hover": "#dc2626",
        "tree_bg": "#101726",
        "tree_fg": "#f1f5f9",
        "tree_alt": "#141c2e",
        "tree_selected": "#283454",
        "tree_header_bg": "#1c2640",
        "tree_header_fg": "#cbd5e1",
        "input_bg": "#101726",
        "input_fg": "#f8fafc",
        "status_bg": "#0d1320",
        "status_fg": "#94a3b8",
    },
    "light": {
        "bg": "#f8fafc",
        "card": "#ffffff",
        "card_hover": "#f1f5f9",
        "surface": "#f1f5f9",
        "surface_hover": "#e2e8f0",
        "border": "#e2e8f0",
        "border_focus": "#4f46e5",
        "text": "#0f172a",
        "text_secondary": "#475569",
        "text_muted": "#94a3b8",
        "accent": "#4f46e5",
        "accent_hover": "#4338ca",
        "accent_text": "#ffffff",
        "success": "#059669",
        "success_hover": "#047857",
        "warning": "#d97706",
        "warning_hover": "#b45309",
        "danger": "#dc2626",
        "danger_hover": "#b91c1c",
        "tree_bg": "#ffffff",
        "tree_fg": "#0f172a",
        "tree_alt": "#f8fafc",
        "tree_selected": "#e0e7ff",
        "tree_header_bg": "#f1f5f9",
        "tree_header_fg": "#334155",
        "input_bg": "#ffffff",
        "input_fg": "#0f172a",
        "status_bg": "#e2e8f0",
        "status_fg": "#475569",
    }
}

# Category icon badges
CATEGORY_ICONS = {
    "Documents": "📄",
    "Images": "🖼️",
    "Videos": "🎬",
    "Music": "🎵",
    "Archives": "📦",
    "Applications": "⚙️",
    "Code": "💻",
    "Others": "📁",
}


# ============================================================================
# MODERN ROUNDED BUTTON WIDGET (CANVAS-BASED FOR FLAWLESS MAC RENDERING)
# ============================================================================

class ModernButton(tk.Canvas):
    """
    Cross-platform rounded button implemented via Canvas.
    Renders gorgeous smooth pill buttons with custom tints and hover effects on macOS,
    where standard tk.Button ignores background colors.
    """
    def __init__(
        self, parent, text, command=None, bg="#6366f1", hover_bg="#4f46e5",
        fg="#ffffff", font=("Segoe UI", 10, "bold"), radius=8,
        padx=14, pady=7, outline="", active_bg=None, **kwargs
    ):
        super().__init__(parent, highlightthickness=0, bd=0, **kwargs)
        self.text = text
        self.command = command
        self.btn_bg = bg
        self.btn_hover_bg = hover_bg
        self.btn_active_bg = active_bg or hover_bg
        self.btn_fg = fg
        self.btn_font = font
        self.radius = radius
        self.padx = padx
        self.pady = pady
        self.outline = outline
        self.is_hover = False
        self.is_pressed = False
        self.is_disabled = False

        self._calc_size()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.configure(cursor="hand2")
        self.render()

    def _calc_size(self):
        try:
            font_obj = tkfont.Font(font=self.btn_font)
            text_w = font_obj.measure(self.text)
            text_h = font_obj.metrics("linespace")
        except Exception:
            text_w = len(self.text) * 8
            text_h = 16

        self.w = max(text_w + self.padx * 2, 60)
        self.h = max(text_h + self.pady * 2, 28)
        self.configure(width=self.w, height=self.h)

    def set_theme_colors(self, bg, hover_bg, fg=None, outline=None):
        self.btn_bg = bg
        self.btn_hover_bg = hover_bg
        self.btn_active_bg = hover_bg
        if fg:
            self.btn_fg = fg
        if outline is not None:
            self.outline = outline
        self.render()

    def set_text(self, new_text):
        self.text = new_text
        self._calc_size()
        self.render()

    def set_disabled(self, disabled=True):
        self.is_disabled = disabled
        self.configure(cursor="" if disabled else "hand2")
        self.render()

    def render(self):
        self.delete("all")
        if self.is_disabled:
            fill_color = "#334155" if self.btn_bg.startswith("#") and self.btn_bg[1:3] in ["63", "10", "4f"] else "#cbd5e1"
            text_color = "#94a3b8"
        elif self.is_pressed:
            fill_color = self.btn_active_bg
            text_color = self.btn_fg
        elif self.is_hover:
            fill_color = self.btn_hover_bg
            text_color = self.btn_fg
        else:
            fill_color = self.btn_bg
            text_color = self.btn_fg

        w, h = self.w, self.h
        r = min(self.radius, h // 2)

        # Smooth polygon points for rounded pill
        pts = [
            2 + r, 2,
            w - 2 - r, 2,
            w - 2, 2,
            w - 2, 2 + r,
            w - 2, h - 2 - r,
            w - 2, h - 2,
            w - 2 - r, h - 2,
            2 + r, h - 2,
            2, h - 2,
            2, h - 2 - r,
            2, 2 + r,
            2, 2
        ]
        self.create_polygon(pts, smooth=True, fill=fill_color, outline=self.outline)
        self.create_text(w / 2, h / 2, text=self.text, fill=text_color, font=self.btn_font)

    def _on_enter(self, e):
        if not self.is_disabled:
            self.is_hover = True
            self.render()

    def _on_leave(self, e):
        self.is_hover = False
        self.is_pressed = False
        self.render()

    def _on_press(self, e):
        if not self.is_disabled:
            self.is_pressed = True
            self.render()

    def _on_release(self, e):
        if not self.is_disabled and self.is_pressed:
            self.is_pressed = False
            self.render()
            if self.command:
                self.command()


# ============================================================================
# STORAGE DISTRIBUTION CANVAS BAR
# ============================================================================

class StorageDistributionBar(tk.Canvas):
    """
    Renders an aesthetic horizontal stacked bar chart showing file distribution by category,
    resembling the macOS 'About This Mac' storage bar.
    """
    def __init__(self, parent, height=14, **kwargs):
        super().__init__(parent, height=height, highlightthickness=0, bd=0, **kwargs)
        self.segments = []  # list of (category, ratio, color)
        self.bar_bg = "#1e293b"
        self.bind("<Configure>", lambda e: self.render())

    def update_data(self, categories_data, total_size, theme_tokens):
        self.bar_bg = theme_tokens["surface"]
        self.configure(bg=theme_tokens["card"])
        self.segments.clear()

        if total_size <= 0:
            self.render()
            return

        for category, data in sorted(categories_data.items(), key=lambda x: x[1]["size"], reverse=True):
            size = data["size"]
            if size > 0:
                ratio = size / total_size
                color = CATEGORY_COLORS.get(category, "#64748b")
                self.segments.append((category, ratio, color))

        self.render()

    def render(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 10 or h <= 4:
            return

        radius = h // 2
        # Background empty bar
        self._draw_pill(2, 2, w - 2, h - 2, radius, self.bar_bg)

        if not self.segments:
            return

        # Stacked category segments
        cur_x = 2
        total_w = w - 4
        for idx, (cat, ratio, color) in enumerate(self.segments):
            seg_w = max(round(total_w * ratio), 4)
            next_x = min(cur_x + seg_w, w - 2)
            if idx == len(self.segments) - 1:
                next_x = w - 2

            if next_x > cur_x:
                self.create_rectangle(cur_x, 2, next_x, h - 2, fill=color, outline="")
                cur_x = next_x

    def _draw_pill(self, x1, y1, x2, y2, r, fill):
        pts = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1
        ]
        self.create_polygon(pts, smooth=True, fill=fill, outline="")


# ============================================================================
# CROSS-PLATFORM SYSTEM ACTIONS
# ============================================================================

def reveal_in_file_manager(path_str):
    """Reveals the target file in the native system file explorer."""
    try:
        p = Path(path_str).resolve()
        if not p.exists():
            return
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", str(p)], check=False)
        elif sys.platform == "win32":
            subprocess.run(["explorer", f"/select,{str(p)}"], check=False)
        else:
            subprocess.run(["xdg-open", str(p.parent)], check=False)
    except Exception as e:
        print(f"Error revealing in file manager: {e}")

def open_file_default(path_str):
    """Opens the target file with the system default application."""
    try:
        p = Path(path_str).resolve()
        if not p.exists():
            return
        if sys.platform == "darwin":
            subprocess.run(["open", str(p)], check=False)
        elif sys.platform == "win32":
            os.startfile(str(p))
        else:
            subprocess.run(["xdg-open", str(p)], check=False)
    except Exception as e:
        print(f"Error opening file: {e}")

def delete_to_trash(path_str):
    """Safely moves a file to the native system Trash."""
    p = Path(path_str).resolve()
    if not p.exists():
        return False
    if HAS_SEND2TRASH:
        send2trash.send2trash(str(p))
    else:
        p.unlink()
    return True


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class FileSenseApp:
    def __init__(self, root):
        self.root = root
        self.theme_name = "dark"
        self.tokens = THEMES[self.theme_name]

        self.root.title("FileSense — Smart File Organizer & Duplicate Detector")
        self.root.geometry("1120x760")
        self.root.minsize(960, 640)
        self.root.configure(bg=self.tokens["bg"])

        # Center window on screen
        self._center_window(1120, 760)

        # State
        self.folder = None
        self.files = []
        self.duplicates = []
        self.filtered_files = []
        self.is_scanning = False
        self.sort_directions = {}

        # StringVars
        self.folder_var = tk.StringVar(value="No folder selected")
        self.status_var = tk.StringVar(value="Select a folder or click 'Demo Data' to begin.")
        self.total_var = tk.StringVar(value="0")
        self.size_var = tk.StringVar(value="0 B")
        self.dup_var = tk.StringVar(value="0")
        self.recover_var = tk.StringVar(value="0 B")
        self.search_var = tk.StringVar(value="")
        self.search_var.trace_add("write", lambda *args: self._on_search_changed())

        # Widget registry for theme updates
        self.theme_buttons = []
        self.theme_frames = []
        self.theme_labels = []

        # Configure TTK Styles
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._apply_ttk_styles()

        # Thread communication queue
        self.queue = queue.Queue()
        self._poll_queue()

        # Build UI layout
        self.build_ui()

        # Bring window to front
        self.root.update_idletasks()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _poll_queue(self):
        """Processes thread-safe messages from background workers."""
        try:
            while True:
                msg_type, payload = self.queue.get_nowait()
                if msg_type == "progress":
                    pct, name = payload
                    self.status_var.set(f"Analyzing duplicates: {pct}% ({name[:25]})...")
                elif msg_type == "done":
                    scanned, dups, elapsed = payload
                    self._on_scan_completed(scanned, dups, elapsed)
                elif msg_type == "error":
                    self._on_scan_failed(payload)
        except queue.Empty:
            pass
        finally:
            self.root.after(40, self._poll_queue)

    def _center_window(self, width, height):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2 - 30)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _apply_ttk_styles(self):
        t = self.tokens
        # Treeview styling
        self.style.configure(
            "Custom.Treeview",
            background=t["tree_bg"],
            foreground=t["tree_fg"],
            fieldbackground=t["tree_bg"],
            rowheight=28,
            font=("Segoe UI", 10),
            borderwidth=0
        )
        self.style.map(
            "Custom.Treeview",
            background=[("selected", t["tree_selected"])],
            foreground=[("selected", "#ffffff")]
        )
        self.style.configure(
            "Custom.Treeview.Heading",
            background=t["tree_header_bg"],
            foreground=t["tree_header_fg"],
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=(8, 6)
        )
        self.style.map(
            "Custom.Treeview.Heading",
            background=[("active", t["surface_hover"])],
            foreground=[("active", t["text"])]
        )

        # Progressbar styling
        self.style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=t["surface"],
            background=t["accent"],
            bordercolor=t["border"],
            lightcolor=t["accent"],
            darkcolor=t["accent"],
            thickness=6
        )

        # Combobox styling
        self.style.configure(
            "Custom.TCombobox",
            fieldbackground=t["input_bg"],
            background=t["surface"],
            foreground=t["text"],
            arrowcolor=t["text"],
            padding=5
        )

    # ------------------------------------------------------------------------
    # UI CONSTRUCTION
    # ------------------------------------------------------------------------

    def build_ui(self):
        t = self.tokens

        # TOP BAR / HEADER
        self.header_frame = tk.Frame(self.root, bg=t["bg"])
        self.header_frame.pack(fill="x", padx=24, pady=(16, 6))

        # Title & Subtitle + Theme Toggle in top header
        top_row = tk.Frame(self.header_frame, bg=t["bg"])
        top_row.pack(fill="x", pady=(0, 10))

        title_box = tk.Frame(top_row, bg=t["bg"])
        title_box.pack(side="left")

        self.title_lbl = tk.Label(
            title_box,
            text="FileSense",
            font=("Segoe UI", 22, "bold"),
            bg=t["bg"],
            fg=t["text"]
        )
        self.title_lbl.pack(anchor="w")

        self.subtitle_lbl = tk.Label(
            title_box,
            text="Smart File Organizer & Duplicate Storage Analyzer",
            font=("Segoe UI", 10),
            bg=t["bg"],
            fg=t["text_muted"]
        )
        self.subtitle_lbl.pack(anchor="w")

        # Top Right Actions: Theme Toggle & About
        top_actions = tk.Frame(top_row, bg=t["bg"])
        top_actions.pack(side="right", pady=4)

        self.theme_btn = ModernButton(
            top_actions,
            text="🌙 Dark Mode" if self.theme_name == "dark" else "☀️ Light Mode",
            command=self.toggle_theme,
            bg=t["surface"],
            hover_bg=t["surface_hover"],
            fg=t["text"],
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=6,
            radius=6
        )
        self.theme_btn.pack(side="right", padx=(6, 0))

        self.about_btn = ModernButton(
            top_actions,
            text="ℹ️ About",
            command=self.show_about,
            bg=t["surface"],
            hover_bg=t["surface_hover"],
            fg=t["text_secondary"],
            font=("Segoe UI", 9),
            padx=10,
            pady=6,
            radius=6
        )
        self.about_btn.pack(side="right")

        # FOLDER SELECTION BAR
        folder_bar = tk.Frame(self.header_frame, bg=t["card"], padx=10, pady=8)
        folder_bar.pack(fill="x")
        self.folder_bar_frame = folder_bar

        folder_icon = tk.Label(folder_bar, text="📁", font=("Segoe UI", 13), bg=t["card"], fg=t["accent"])
        folder_icon.pack(side="left", padx=(4, 8))
        self.folder_icon_lbl = folder_icon

        self.folder_entry = tk.Entry(
            folder_bar,
            textvariable=self.folder_var,
            font=("Segoe UI", 11),
            relief="flat",
            bg=t["input_bg"],
            fg=t["text"],
            insertbackground=t["text"],
            highlightthickness=1,
            highlightbackground=t["border"],
            highlightcolor=t["accent"]
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 10))

        self.browse_btn = ModernButton(
            folder_bar,
            text="Browse...",
            command=self.select_folder,
            bg=t["surface"],
            hover_bg=t["surface_hover"],
            fg=t["text"],
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=6,
            radius=6
        )
        self.browse_btn.pack(side="left", padx=(0, 6))

        self.demo_btn = ModernButton(
            folder_bar,
            text="🧪 Demo Data",
            command=self.load_demo_data,
            bg=t["surface"],
            hover_bg=t["surface_hover"],
            fg=t["warning"],
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=6,
            radius=6
        )
        self.demo_btn.pack(side="left", padx=(0, 8))

        self.scan_btn = ModernButton(
            folder_bar,
            text="⚡ SCAN FOLDER",
            command=self.start_scan_thread,
            bg=t["accent"],
            hover_bg=t["accent_hover"],
            fg=t["accent_text"],
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=6,
            radius=6
        )
        self.scan_btn.pack(side="left")

        # METRIC CARDS ROW
        self.cards_frame = tk.Frame(self.root, bg=t["bg"])
        self.cards_frame.pack(fill="x", padx=24, pady=(10, 6))

        self.card_total = self._build_stat_card(
            self.cards_frame, 0, "TOTAL FILES", self.total_var, "📁", "#3b82f6", "Scanned files"
        )
        self.card_size = self._build_stat_card(
            self.cards_frame, 1, "TOTAL STORAGE", self.size_var, "💾", "#8b5cf6", "Storage footprint"
        )
        self.card_dup = self._build_stat_card(
            self.cards_frame, 2, "DUPLICATES", self.dup_var, "⚠️", "#f59e0b", "Redundant copies"
        )
        self.card_recover = self._build_stat_card(
            self.cards_frame, 3, "RECOVERABLE", self.recover_var, "♻️", "#10b981", "Wasted disk space"
        )

        # STATUS BAR (pack at bottom first)
        self.status_bar = tk.Frame(self.root, bg=t["status_bg"], padx=14, pady=6)
        self.status_bar.pack(fill="x", side="bottom")

        self.status_lbl = tk.Label(
            self.status_bar,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            bg=t["status_bg"],
            fg=t["status_fg"],
            anchor="w"
        )
        self.status_lbl.pack(side="left")

        # BOTTOM ACTION BAR (pack directly above status bar)
        self.bottom_bar = tk.Frame(self.root, bg=t["bg"])
        self.bottom_bar.pack(fill="x", side="bottom", padx=24, pady=(2, 6))

        self.organize_btn = ModernButton(
            self.bottom_bar,
            text="✨ Organize Files into Categories",
            command=self.confirm_organize,
            bg=t["accent"],
            hover_bg=t["accent_hover"],
            fg=t["accent_text"],
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=7,
            radius=6
        )
        self.organize_btn.pack(side="left", padx=(0, 8))

        self.report_btn = ModernButton(
            self.bottom_bar,
            text="📄 Export Full Report",
            command=self.save_report,
            bg=t["surface"],
            hover_bg=t["surface_hover"],
            fg=t["text"],
            font=("Segoe UI", 10),
            padx=14,
            pady=7,
            radius=6
        )
        self.report_btn.pack(side="left")

        # Scan progress bar (hidden by default)
        self.progress_bar = ttk.Progressbar(
            self.bottom_bar,
            style="Custom.Horizontal.TProgressbar",
            orient="horizontal",
            mode="indeterminate"
        )

        # MAIN RESULT AREA (CONTAINER - expands to fill cavity)
        self.container_frame = tk.Frame(self.root, bg=t["card"])
        self.container_frame.pack(fill="both", expand=True, padx=24, pady=(6, 8))

        # TAB NAVIGATION BAR
        self.tabs_nav = tk.Frame(self.container_frame, bg=t["surface"], padx=8, pady=6)
        self.tabs_nav.pack(fill="x")

        self.tab_buttons = {}
        tab_specs = [
            ("Summary", "📊 Category Overview"),
            ("Duplicates", "⚠️ Duplicates"),
            ("AllFiles", "🔍 Scanned Files"),
            ("LargeFiles", "📈 Largest Files"),
        ]

        for key, label in tab_specs:
            btn = ModernButton(
                self.tabs_nav,
                text=label,
                command=lambda k=key: self.switch_tab(k),
                bg=t["accent"] if key == "Summary" else t["surface"],
                hover_bg=t["accent_hover"] if key == "Summary" else t["surface_hover"],
                fg="#ffffff" if key == "Summary" else t["text_secondary"],
                font=("Segoe UI", 9, "bold"),
                padx=14,
                pady=6,
                radius=6
            )
            btn.pack(side="left", padx=3)
            self.tab_buttons[key] = btn

        # TAB CONTENT HOST
        self.tab_content = tk.Frame(self.container_frame, bg=t["card"])
        self.tab_content.pack(fill="both", expand=True, padx=12, pady=10)

        # Build individual tabs
        self.tab_views = {}
        self._build_tab_summary()
        self._build_tab_duplicates()
        self._build_tab_all_files()
        self._build_tab_large_files()

        # Show initial tab
        self.active_tab = "Summary"
        self.tab_views["Summary"].pack(fill="both", expand=True)

    def _build_stat_card(self, parent, col, title, var, icon, accent_color, subtitle):
        t = self.tokens
        parent.columnconfigure(col, weight=1)

        card = tk.Frame(parent, bg=t["card"], padx=14, pady=10)
        card.grid(row=0, column=col, padx=4, sticky="nsew")

        top_line = tk.Frame(card, bg=t["card"])
        top_line.pack(fill="x")

        icon_lbl = tk.Label(
            top_line,
            text=icon,
            font=("Segoe UI", 12),
            bg=t["card"],
            fg=accent_color
        )
        icon_lbl.pack(side="left")

        title_lbl = tk.Label(
            top_line,
            text=title,
            font=("Segoe UI", 8, "bold"),
            bg=t["card"],
            fg=t["text_muted"]
        )
        title_lbl.pack(side="left", padx=(6, 0))

        val_lbl = tk.Label(
            card,
            textvariable=var,
            font=("Segoe UI", 18, "bold"),
            bg=t["card"],
            fg=t["text"]
        )
        val_lbl.pack(anchor="w", pady=(4, 0))

        sub_lbl = tk.Label(
            card,
            text=subtitle,
            font=("Segoe UI", 8),
            bg=t["card"],
            fg=t["text_secondary"]
        )
        sub_lbl.pack(anchor="w")

        return card

    # ------------------------------------------------------------------------
    # TAB 1: SUMMARY & STORAGE OVERVIEW
    # ------------------------------------------------------------------------

    def _build_tab_summary(self):
        t = self.tokens
        frame = tk.Frame(self.tab_content, bg=t["card"])
        self.tab_views["Summary"] = frame

        # Top section: Visual Distribution Bar
        dist_box = tk.Frame(frame, bg=t["surface"], padx=14, pady=10)
        dist_box.pack(fill="x", pady=(0, 10))
        self.dist_box_frame = dist_box

        bar_title = tk.Label(
            dist_box,
            text="Storage Distribution Breakdown",
            font=("Segoe UI", 10, "bold"),
            bg=t["surface"],
            fg=t["text"]
        )
        bar_title.pack(anchor="w", pady=(0, 6))

        self.storage_bar = StorageDistributionBar(dist_box, height=16)
        self.storage_bar.pack(fill="x", pady=(2, 6))

        self.legend_frame = tk.Frame(dist_box, bg=t["surface"])
        self.legend_frame.pack(fill="x")

        # Category Table
        table_container = tk.Frame(frame, bg=t["card"])
        table_container.pack(fill="both", expand=True)

        cols = ("category", "files", "size", "percent")
        self.summary_tree = ttk.Treeview(
            table_container,
            columns=cols,
            show="headings",
            style="Custom.Treeview"
        )
        self.summary_tree.heading("category", text="Category")
        self.summary_tree.heading("files", text="Files")
        self.summary_tree.heading("size", text="Total Storage")
        self.summary_tree.heading("percent", text="Share of Total")

        self.summary_tree.column("category", width=220, anchor="w")
        self.summary_tree.column("files", width=120, anchor="center")
        self.summary_tree.column("size", width=160, anchor="e")
        self.summary_tree.column("percent", width=140, anchor="e")

        scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.summary_tree.yview)
        self.summary_tree.configure(yscrollcommand=scrollbar.set)

        self.summary_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # ------------------------------------------------------------------------
    # TAB 2: DUPLICATES EXPLORER
    # ------------------------------------------------------------------------

    def _build_tab_duplicates(self):
        t = self.tokens
        frame = tk.Frame(self.tab_content, bg=t["card"])
        self.tab_views["Duplicates"] = frame

        # Duplicates action toolbar
        dup_toolbar = tk.Frame(frame, bg=t["surface"], padx=10, pady=8)
        dup_toolbar.pack(fill="x", pady=(0, 8))
        self.dup_toolbar_frame = dup_toolbar

        self.dup_select_btn = ModernButton(
            dup_toolbar,
            text="✓ Select Duplicate Copies",
            command=self.select_duplicate_copies,
            bg=t["surface_hover"],
            hover_bg=t["border"],
            fg=t["text"],
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=5,
            radius=6
        )
        self.dup_select_btn.pack(side="left", padx=(0, 6))

        self.dup_clear_btn = ModernButton(
            dup_toolbar,
            text="✗ Clear Selection",
            command=lambda: self.dup_tree.selection_remove(self.dup_tree.selection()),
            bg=t["surface_hover"],
            hover_bg=t["border"],
            fg=t["text_secondary"],
            font=("Segoe UI", 9),
            padx=10,
            pady=5,
            radius=6
        )
        self.dup_clear_btn.pack(side="left", padx=(0, 12))

        self.dup_delete_btn = ModernButton(
            dup_toolbar,
            text="🗑️ Move Selected to Trash",
            command=self.delete_selected_duplicates,
            bg=t["danger"],
            hover_bg=t["danger_hover"],
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=5,
            radius=6
        )
        self.dup_delete_btn.pack(side="left", padx=(0, 8))

        self.dup_reveal_btn = ModernButton(
            dup_toolbar,
            text="📂 Reveal in Finder",
            command=self._reveal_selected_dup,
            bg=t["surface_hover"],
            hover_bg=t["border"],
            fg=t["text_secondary"],
            font=("Segoe UI", 9),
            padx=10,
            pady=5,
            radius=6
        )
        self.dup_reveal_btn.pack(side="right")

        # Duplicates Treeview
        tree_container = tk.Frame(frame, bg=t["card"])
        tree_container.pack(fill="both", expand=True)

        cols = ("role", "name", "category", "size", "modified", "path")
        self.dup_tree = ttk.Treeview(
            tree_container,
            columns=cols,
            show="tree headings",
            style="Custom.Treeview",
            selectmode="extended"
        )
        self.dup_tree.heading("#0", text="Group / Status")
        self.dup_tree.heading("role", text="Role")
        self.dup_tree.heading("name", text="File Name")
        self.dup_tree.heading("category", text="Category")
        self.dup_tree.heading("size", text="Size")
        self.dup_tree.heading("modified", text="Modified")
        self.dup_tree.heading("path", text="Full Path")

        self.dup_tree.column("#0", width=180, anchor="w")
        self.dup_tree.column("role", width=110, anchor="center")
        self.dup_tree.column("name", width=190, anchor="w")
        self.dup_tree.column("category", width=110, anchor="w")
        self.dup_tree.column("size", width=110, anchor="e")
        self.dup_tree.column("modified", width=150, anchor="center")
        self.dup_tree.column("path", width=320, anchor="w")

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.dup_tree.yview)
        self.dup_tree.configure(yscrollcommand=scrollbar.set)

        self.dup_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.dup_tree.bind("<Double-1>", lambda e: self._on_dup_double_click())
        self._setup_context_menu(self.dup_tree)

    # ------------------------------------------------------------------------
    # TAB 3: ALL SCANNED FILES (WITH INSTANT SEARCH & FILTER)
    # ------------------------------------------------------------------------

    def _build_tab_all_files(self):
        t = self.tokens
        frame = tk.Frame(self.tab_content, bg=t["card"])
        self.tab_views["AllFiles"] = frame

        # Search & Filter bar
        filter_bar = tk.Frame(frame, bg=t["surface"], padx=10, pady=8)
        filter_bar.pack(fill="x", pady=(0, 8))
        self.all_filter_frame = filter_bar

        search_icon = tk.Label(filter_bar, text="🔍", font=("Segoe UI", 11), bg=t["surface"], fg=t["text_muted"])
        search_icon.pack(side="left", padx=(2, 6))

        self.search_entry = tk.Entry(
            filter_bar,
            textvariable=self.search_var,
            font=("Segoe UI", 10),
            relief="flat",
            bg=t["input_bg"],
            fg=t["text"],
            insertbackground=t["text"],
            highlightthickness=1,
            highlightbackground=t["border"],
            highlightcolor=t["accent"]
        )
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 10))

        cat_lbl = tk.Label(filter_bar, text="Category:", font=("Segoe UI", 9, "bold"), bg=t["surface"], fg=t["text_secondary"])
        cat_lbl.pack(side="left", padx=(4, 4))

        self.category_filter_var = tk.StringVar(value="All Categories")
        self.category_combo = ttk.Combobox(
            filter_bar,
            textvariable=self.category_filter_var,
            state="readonly",
            values=["All Categories"],
            style="Custom.TCombobox",
            width=16
        )
        self.category_combo.pack(side="left", padx=(0, 10))
        self.category_combo.bind("<<ComboboxSelected>>", lambda e: self._filter_and_render_all_files())

        self.match_count_lbl = tk.Label(
            filter_bar,
            text="0 files",
            font=("Segoe UI", 9),
            bg=t["surface"],
            fg=t["text_muted"]
        )
        self.match_count_lbl.pack(side="right")

        # Files Treeview
        tree_container = tk.Frame(frame, bg=t["card"])
        tree_container.pack(fill="both", expand=True)

        cols = ("name", "category", "size", "modified", "path")
        self.files_tree = ttk.Treeview(
            tree_container,
            columns=cols,
            show="headings",
            style="Custom.Treeview"
        )

        for col, title, width, anchor in [
            ("name", "File Name", 240, "w"),
            ("category", "Category", 120, "w"),
            ("size", "Size", 120, "e"),
            ("modified", "Date Modified", 160, "center"),
            ("path", "File Location", 400, "w"),
        ]:
            self.files_tree.heading(col, text=title, command=lambda c=col: self._sort_tree(self.files_tree, c))
            self.files_tree.column(col, width=width, anchor=anchor)

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=scrollbar.set)

        self.files_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.files_tree.bind("<Double-1>", lambda e: self._on_file_double_click(self.files_tree))
        self._setup_context_menu(self.files_tree)

    # ------------------------------------------------------------------------
    # TAB 4: LARGEST FILES
    # ------------------------------------------------------------------------

    def _build_tab_large_files(self):
        t = self.tokens
        frame = tk.Frame(self.tab_content, bg=t["card"])
        self.tab_views["LargeFiles"] = frame

        tree_container = tk.Frame(frame, bg=t["card"])
        tree_container.pack(fill="both", expand=True)

        cols = ("rank", "name", "category", "size", "modified", "path")
        self.large_tree = ttk.Treeview(
            tree_container,
            columns=cols,
            show="headings",
            style="Custom.Treeview"
        )

        for col, title, width, anchor in [
            ("rank", "Rank", 70, "center"),
            ("name", "File Name", 240, "w"),
            ("category", "Category", 120, "w"),
            ("size", "File Size", 130, "e"),
            ("modified", "Date Modified", 160, "center"),
            ("path", "Path", 400, "w"),
        ]:
            self.large_tree.heading(col, text=title)
            self.large_tree.column(col, width=width, anchor=anchor)

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.large_tree.yview)
        self.large_tree.configure(yscrollcommand=scrollbar.set)

        self.large_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.large_tree.bind("<Double-1>", lambda e: self._on_file_double_click(self.large_tree))
        self._setup_context_menu(self.large_tree)

    # ------------------------------------------------------------------------
    # CONTEXT MENUS & INTERACTIONS
    # ------------------------------------------------------------------------

    def _setup_context_menu(self, tree):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="▶ Open File", command=lambda: self._context_open(tree))
        menu.add_command(label="📂 Reveal in File Manager", command=lambda: self._context_reveal(tree))
        menu.add_command(label="📋 Copy Path", command=lambda: self._context_copy_path(tree))

        def show_popup(event):
            item = tree.identify_row(event.y)
            if item:
                tree.selection_set(item)
                menu.post(event.x_root, event.y_root)

        tree.bind("<Button-2>", show_popup)  # Mac right click
        tree.bind("<Button-3>", show_popup)  # Windows/Linux right click

    def _get_tree_path(self, tree, item_id=None):
        if item_id is None:
            selection = tree.selection()
            if not selection:
                return None
            item_id = selection[0]

        values = tree.item(item_id, "values")
        if not values:
            return None
        # Path is always the last column
        return values[-1]

    def _context_open(self, tree):
        path = self._get_tree_path(tree)
        if path:
            open_file_default(path)

    def _context_reveal(self, tree):
        path = self._get_tree_path(tree)
        if path:
            reveal_in_file_manager(path)

    def _context_copy_path(self, tree):
        path = self._get_tree_path(tree)
        if path:
            self.root.clipboard_clear()
            self.root.clipboard_append(path)
            self.status_var.set(f"Copied path: {path}")

    def _on_file_double_click(self, tree):
        path = self._get_tree_path(tree)
        if path:
            open_file_default(path)

    def _on_dup_double_click(self):
        selection = self.dup_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        values = self.dup_tree.item(item_id, "values")
        if values and len(values) >= 6:
            path = values[5]
            open_file_default(path)

    def _reveal_selected_dup(self):
        selection = self.dup_tree.selection()
        if not selection:
            messagebox.showinfo("Selection Required", "Please select a duplicate file to reveal.")
            return
        item_id = selection[0]
        values = self.dup_tree.item(item_id, "values")
        if values and len(values) >= 6:
            reveal_in_file_manager(values[5])

    # ------------------------------------------------------------------------
    # TAB SWITCHING
    # ------------------------------------------------------------------------

    def switch_tab(self, tab_key):
        if tab_key not in self.tab_views:
            return

        self.active_tab = tab_key
        t = self.tokens

        for key, view in self.tab_views.items():
            if key == tab_key:
                view.pack(fill="both", expand=True)
                self.tab_buttons[key].set_theme_colors(
                    t["accent"], t["accent_hover"], "#ffffff"
                )
            else:
                view.pack_forget()
                self.tab_buttons[key].set_theme_colors(
                    t["surface"], t["surface_hover"], t["text_secondary"]
                )

    # ------------------------------------------------------------------------
    # SCANNING & BACKGROUND WORKER
    # ------------------------------------------------------------------------

    def select_folder(self):
        chosen = filedialog.askdirectory(title="Choose a folder to scan with FileSense")
        if chosen:
            self.folder = Path(chosen).resolve()
            self.folder_var.set(str(self.folder))
            self.status_var.set(f"Folder selected: {self.folder.name}. Click 'SCAN FOLDER'.")

    def load_demo_data(self):
        try:
            demo_path = create_demo_data()
            self.folder = demo_path
            self.folder_var.set(str(demo_path))
            self.status_var.set("Demo folder ready! Starting scan...")
            self.start_scan_thread()
        except Exception as e:
            messagebox.showerror("Demo Setup Error", str(e))

    def start_scan_thread(self):
        if self.is_scanning:
            return

        if not self.folder:
            messagebox.showwarning("Folder Required", "Please select a folder or load Demo Data first.")
            return

        self.is_scanning = True
        self.scan_btn.set_disabled(True)
        self.scan_btn.set_text("Scanning...")
        self.progress_bar.pack(side="right", padx=10, fill="x", expand=False)
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start(10)
        self.status_var.set("Scanning directory recursively...")

        # Run scan and duplicate analysis in background thread
        worker = threading.Thread(target=self._run_scan_worker, daemon=True)
        worker.start()

    def _run_scan_worker(self):
        start_time = time.time()
        try:
            # 1. Scan files
            scanned = scan_folder(self.folder)

            def dup_progress(cur, total, name):
                if total > 0:
                    pct = int((cur / total) * 100)
                    self.queue.put(("progress", (pct, name)))

            # 2. Duplicate detection with two-pass hashing & progress
            dups = find_duplicates(scanned, progress_callback=dup_progress)
            elapsed = time.time() - start_time

            # Post completion event to queue
            self.queue.put(("done", (scanned, dups, elapsed)))

        except Exception as e:
            self.queue.put(("error", str(e)))

    def _on_scan_completed(self, scanned_files, duplicate_groups, elapsed_time):
        self.files = scanned_files
        self.duplicates = duplicate_groups
        self.is_scanning = False

        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.scan_btn.set_disabled(False)
        self.scan_btn.set_text("⚡ SCAN FOLDER")

        # Update Metrics
        total_size = sum(item["size"] for item in self.files)
        dup_count = sum(len(group) - 1 for group in self.duplicates)
        recover_size = sum(item["size"] for group in self.duplicates for item in group[1:])

        self.total_var.set(f"{len(self.files):,}")
        self.size_var.set(format_size(total_size))
        self.dup_var.set(f"{dup_count:,}")
        self.recover_var.set(format_size(recover_size))

        # Update category filter dropdown values
        all_categories = sorted(list(set(item["category"] for item in self.files)))
        self.category_combo["values"] = ["All Categories"] + all_categories
        self.category_filter_var.set("All Categories")

        # Populate all tab views
        self._render_summary_tab(total_size)
        self._render_duplicates_tab()
        self._filter_and_render_all_files()
        self._render_large_files_tab()

        self.status_var.set(f"✓ Scan completed in {elapsed_time:.2f}s: {len(self.files)} files, {dup_count} duplicates found.")

    def _on_scan_failed(self, error_message):
        self.is_scanning = False
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.scan_btn.set_disabled(False)
        self.scan_btn.set_text("⚡ SCAN FOLDER")
        self.status_var.set("Scan failed.")
        messagebox.showerror("Scan Error", f"An error occurred while scanning:\n{error_message}")

    # ------------------------------------------------------------------------
    # TAB RENDERING
    # ------------------------------------------------------------------------

    def _render_summary_tab(self, total_size):
        # Clear existing summary rows
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)

        # Clear legend chips
        for widget in self.legend_frame.winfo_children():
            widget.destroy()

        categories_data = defaultdict(lambda: {"count": 0, "size": 0})
        for item in self.files:
            c = item["category"]
            categories_data[c]["count"] += 1
            categories_data[c]["size"] += item["size"]

        # Update Storage Distribution Bar
        self.storage_bar.update_data(categories_data, total_size, self.tokens)

        # Build legend chips
        for category, data in sorted(categories_data.items(), key=lambda x: x[1]["size"], reverse=True):
            pct = (data["size"] / total_size * 100) if total_size > 0 else 0
            color = CATEGORY_COLORS.get(category, "#64748b")
            icon = CATEGORY_ICONS.get(category, "📁")

            chip = tk.Frame(self.legend_frame, bg=self.tokens["surface"], padx=4, pady=2)
            chip.pack(side="left", padx=6, pady=2)

            dot = tk.Label(chip, text="●", fg=color, bg=self.tokens["surface"], font=("Segoe UI", 10))
            dot.pack(side="left")

            txt = tk.Label(
                chip,
                text=f"{icon} {category}: {format_size(data['size'])} ({pct:.1f}%)",
                fg=self.tokens["text"],
                bg=self.tokens["surface"],
                font=("Segoe UI", 8, "bold")
            )
            txt.pack(side="left", padx=(2, 0))

        # Insert rows into Treeview with alternating tag colors
        for category, data in sorted(categories_data.items(), key=lambda x: x[1]["size"], reverse=True):
            pct_str = f"{(data['size'] / total_size * 100):.1f}%" if total_size > 0 else "0%"
            icon = CATEGORY_ICONS.get(category, "📁")
            self.summary_tree.insert(
                "",
                "end",
                values=(
                    f"{icon}  {category}",
                    f"{data['count']:,}",
                    format_size(data["size"]),
                    pct_str
                )
            )

    def _render_duplicates_tab(self):
        for item in self.dup_tree.get_children():
            self.dup_tree.delete(item)

        if not self.duplicates:
            empty_id = self.dup_tree.insert("", "end", text="No duplicates detected", values=("✓", "All files are unique", "", "", "", ""))
            return

        for group_idx, group in enumerate(self.duplicates, 1):
            recoverable = sum(item["size"] for item in group[1:])
            group_id = self.dup_tree.insert(
                "",
                "end",
                text=f"Group {group_idx} ({len(group)} copies)",
                values=(
                    f"{len(group) - 1} copies",
                    f"Recoverable: {format_size(recoverable)}",
                    "",
                    format_size(group[0]["size"]),
                    "",
                    ""
                ),
                open=True
            )

            for idx, item in enumerate(group):
                is_original = (idx == 0)
                role = "⭐ Original" if is_original else f"Copy #{idx}"
                icon = "⭐" if is_original else "📄"

                self.dup_tree.insert(
                    group_id,
                    "end",
                    text=f"  {icon} {item['name']}",
                    values=(
                        role,
                        item["name"],
                        item["category"],
                        format_size(item["size"]),
                        item["modified"],
                        item["path_str"]
                    ),
                    tags=("original" if is_original else "copy",)
                )

        self.dup_tree.tag_configure("original", foreground=self.tokens["accent"])
        self.dup_tree.tag_configure("copy", foreground=self.tokens["warning"])

    def _render_large_files_tab(self):
        for item in self.large_tree.get_children():
            self.large_tree.delete(item)

        top_files = sorted(self.files, key=lambda x: x["size"], reverse=True)[:25]
        for rank, item in enumerate(top_files, 1):
            icon = CATEGORY_ICONS.get(item["category"], "📁")
            self.large_tree.insert(
                "",
                "end",
                values=(
                    f"#{rank}",
                    f"{icon} {item['name']}",
                    item["category"],
                    format_size(item["size"]),
                    item["modified"],
                    item["path_str"]
                )
            )

    def _on_search_changed(self):
        self._filter_and_render_all_files()

    def _filter_and_render_all_files(self):
        query = self.search_var.get().strip().lower()
        selected_cat = self.category_filter_var.get()

        filtered = []
        for item in self.files:
            if selected_cat != "All Categories" and item["category"] != selected_cat:
                continue
            if query and query not in item["name"].lower() and query not in item["extension"]:
                continue
            filtered.append(item)

        self.filtered_files = filtered

        # Update Tree
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)

        total_match_size = sum(f["size"] for f in filtered)
        self.match_count_lbl.configure(text=f"Showing {len(filtered):,} of {len(self.files):,} files ({format_size(total_match_size)})")

        for item in filtered:
            icon = CATEGORY_ICONS.get(item["category"], "📁")
            self.files_tree.insert(
                "",
                "end",
                values=(
                    f"{icon} {item['name']}",
                    item["category"],
                    format_size(item["size"]),
                    item["modified"],
                    item["path_str"]
                )
            )

    def _sort_tree(self, tree, col):
        current_dir = self.sort_directions.get((tree, col), False)
        new_dir = not current_dir
        self.sort_directions[(tree, col)] = new_dir

        items = [(tree.set(k, col), k) for k in tree.get_children("")]

        # Numeric sorting for size
        if col == "size":
            def parse_size(val):
                parts = val.split()
                if not parts:
                    return 0
                num, unit = float(parts[0]), parts[1]
                mult = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}.get(unit, 1)
                return num * mult
            items.sort(key=lambda t: parse_size(t[0]), reverse=new_dir)
        else:
            items.sort(key=lambda t: t[0].lower(), reverse=new_dir)

        for index, (_, k) in enumerate(items):
            tree.move(k, "", index)

        # Update header arrow indicator
        for c in tree["columns"]:
            heading_text = tree.heading(c)["text"].rstrip(" ▲▼")
            if c == col:
                heading_text += " ▲" if not new_dir else " ▼"
            tree.heading(c, text=heading_text)

    # ------------------------------------------------------------------------
    # DUPLICATE ACTIONS (SELECT & SAFE DELETE)
    # ------------------------------------------------------------------------

    def select_duplicate_copies(self):
        """Selects all duplicate copy items in the duplicate tree, preserving originals."""
        self.dup_tree.selection_remove(self.dup_tree.selection())
        to_select = []
        for parent_id in self.dup_tree.get_children():
            children = self.dup_tree.get_children(parent_id)
            for child_id in children:
                tags = self.dup_tree.item(child_id, "tags")
                if "copy" in tags:
                    to_select.append(child_id)

        if to_select:
            self.dup_tree.selection_set(to_select)
            self.status_var.set(f"Selected {len(to_select)} duplicate copies.")
        else:
            self.status_var.set("No duplicate copies found to select.")

    def delete_selected_duplicates(self):
        selection = self.dup_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select the duplicate file copies you want to remove.")
            return

        # Filter selection to valid file copy items only (ignore group headers)
        valid_items = []
        for item_id in selection:
            values = self.dup_tree.item(item_id, "values")
            if values and len(values) >= 6 and values[5]:
                tags = self.dup_tree.item(item_id, "tags")
                if "copy" in tags:
                    valid_items.append((item_id, values[1], values[5]))  # (id, name, path)

        if not valid_items:
            messagebox.showinfo("Nothing to Delete", "Please select duplicate copy items (originals are protected).")
            return

        trash_mode = "Move to Trash" if HAS_SEND2TRASH else "Permanent Delete"
        confirm = messagebox.askyesno(
            f"Confirm {trash_mode}",
            f"Are you sure you want to {trash_mode.lower()} {len(valid_items)} selected duplicate files?\n\n"
            f"This action will free up disk space while keeping your original files safe.\n\nContinue?"
        )

        if not confirm:
            return

        deleted_count = 0
        failed_count = 0

        for item_id, name, path_str in valid_items:
            try:
                if delete_to_trash(path_str):
                    deleted_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                print(f"Failed to delete {path_str}: {e}")

        # Refresh scan after deletion
        self.status_var.set(f"Deleted {deleted_count} duplicate files ({failed_count} failed). Refreshing...")
        self.start_scan_thread()

    # ------------------------------------------------------------------------
    # ORGANIZER & REPORTS
    # ------------------------------------------------------------------------

    def confirm_organize(self):
        if not self.folder or not self.files:
            messagebox.showwarning("Scan Required", "Please scan a folder before organizing files.")
            return

        confirm = messagebox.askyesno(
            "Confirm Organization",
            f"FileSense will categorize and move {len(self.files)} files into organized subdirectories "
            f"(Documents, Images, Code, etc.) inside:\n\n{self.folder}\n\n"
            f"Any existing category folders will be respected.\n\nDo you want to proceed?"
        )

        if not confirm:
            return

        try:
            moved = organize_files(self.folder, self.files)
            messagebox.showinfo("Organization Complete", f"Successfully organized {moved} files into category folders.")
            self.status_var.set(f"Organization completed: {moved} files organized.")
            self.start_scan_thread()
        except Exception as e:
            messagebox.showerror("Organization Error", str(e))

    def save_report(self):
        if not self.files:
            messagebox.showwarning("No Data", "Please scan a folder before exporting a report.")
            return

        target = filedialog.asksaveasfilename(
            title="Save FileSense Report",
            defaultextension=".txt",
            filetypes=[("Text Report (*.txt)", "*.txt")]
        )

        if not target:
            return

        try:
            generate_report(target, self.folder, self.files, self.duplicates)
            messagebox.showinfo("Report Exported", f"Full scan report saved successfully to:\n{target}")
            self.status_var.set(f"Report saved: {Path(target).name}")
        except Exception as e:
            messagebox.showerror("Report Error", str(e))

    def show_about(self):
        messagebox.showinfo(
            "About FileSense",
            "FileSense — Smart File Organizer & Duplicate Detector\n"
            "Version 2.0 (Modern Edition)\n\n"
            "Features:\n"
            "• Recursive multithreaded directory scanning\n"
            "• High-performance two-pass SHA-256 duplicate detection\n"
            "• Visual storage distribution breakdown\n"
            "• Safe duplicate deletion (moves to native Trash)\n"
            "• Smart category organization\n"
            "• Live instant search and file explorer\n"
            "• Dark & Light aesthetic themes\n\n"
            "Built with Python standard library & Tkinter."
        )

    # ------------------------------------------------------------------------
    # THEME SWITCHING (DARK / LIGHT)
    # ------------------------------------------------------------------------

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.tokens = THEMES[self.theme_name]
        t = self.tokens

        self.root.configure(bg=t["bg"])
        self.header_frame.configure(bg=t["bg"])
        self.cards_frame.configure(bg=t["bg"])
        self.bottom_bar.configure(bg=t["bg"])
        self.status_bar.configure(bg=t["status_bg"])

        self.title_lbl.configure(bg=t["bg"], fg=t["text"])
        self.subtitle_lbl.configure(bg=t["bg"], fg=t["text_muted"])
        self.status_lbl.configure(bg=t["status_bg"], fg=t["status_fg"])

        self.folder_bar_frame.configure(bg=t["card"])
        self.folder_icon_lbl.configure(bg=t["card"])
        self.folder_entry.configure(
            bg=t["input_bg"],
            fg=t["text"],
            insertbackground=t["text"],
            highlightbackground=t["border"]
        )

        # Update cards
        for card in [self.card_total, self.card_size, self.card_dup, self.card_recover]:
            card.configure(bg=t["card"])
            for child in card.winfo_children():
                if isinstance(child, tk.Frame):
                    child.configure(bg=t["card"])
                    for sub in child.winfo_children():
                        if isinstance(sub, (tk.Frame, tk.Label)):
                            sub.configure(bg=t["card"])
                elif isinstance(child, tk.Label):
                    child.configure(bg=t["card"])

        # Update containers and tabs
        self.container_frame.configure(bg=t["card"])
        self.tabs_nav.configure(bg=t["surface"])
        self.tab_content.configure(bg=t["card"])
        for v in self.tab_views.values():
            v.configure(bg=t["card"])

        self.dist_box_frame.configure(bg=t["surface"])
        self.legend_frame.configure(bg=t["surface"])
        self.dup_toolbar_frame.configure(bg=t["surface"])
        self.all_filter_frame.configure(bg=t["surface"])

        self.search_entry.configure(
            bg=t["input_bg"],
            fg=t["text"],
            insertbackground=t["text"],
            highlightbackground=t["border"]
        )

        # Update buttons
        self.theme_btn.set_text("🌙 Dark Mode" if self.theme_name == "dark" else "☀️ Light Mode")
        self.theme_btn.set_theme_colors(t["surface"], t["surface_hover"], t["text"])
        self.about_btn.set_theme_colors(t["surface"], t["surface_hover"], t["text_secondary"])
        self.browse_btn.set_theme_colors(t["surface"], t["surface_hover"], t["text"])
        self.demo_btn.set_theme_colors(t["surface"], t["surface_hover"], t["warning"])
        self.scan_btn.set_theme_colors(t["accent"], t["accent_hover"], t["accent_text"])
        self.organize_btn.set_theme_colors(t["accent"], t["accent_hover"], t["accent_text"])
        self.report_btn.set_theme_colors(t["surface"], t["surface_hover"], t["text"])

        for key, btn in self.tab_buttons.items():
            if key == self.active_tab:
                btn.set_theme_colors(t["accent"], t["accent_hover"], "#ffffff")
            else:
                btn.set_theme_colors(t["surface"], t["surface_hover"], t["text_secondary"])

        self._apply_ttk_styles()

        # Re-render active tab graphics
        if self.files:
            total_size = sum(f["size"] for f in self.files)
            self._render_summary_tab(total_size)
            self._render_duplicates_tab()


if __name__ == "__main__":
    root = tk.Tk()
    app = FileSenseApp(root)
    root.mainloop()
