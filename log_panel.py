import os
import tkinter as tk
from tkinter import ttk

# ── 配色引用 ──────────────────────────────────────────────────────
BG_DARK = "#0d1117"
BG_SURFACE = "#161b22"
BG_ELEVATED = "#1c2128"
BG_HEADER_LOG = "#1a3a4a"
ACCENT_BLUE = "#58a6ff"
ACCENT_GREEN = "#3fb950"
ACCENT_RED = "#f85149"
TEXT_PRIMARY = "#c9d1d9"
TEXT_SECONDARY = "#8b949e"
BORDER_COLOR = "#30363d"


class LogPanel(ttk.Frame):
    def __init__(self, parent, config_item, on_config_change=None, _popup=False):
        super().__init__(parent)
        self.log_path = config_item["path"]
        self.display_lines = config_item["lines"]
        self.refresh_ms = config_item["refresh_ms"]
        self.order = config_item.get("order", "asc")
        self._config_item = config_item
        self._on_config_change = on_config_change
        self._content_parent = None
        self._toplevel = None
        self._detached_panel = None
        self._popup = _popup
        self._active = True

        self._build_ui()
        self._schedule_refresh()

    def stop_refresh(self):
        self._active = False

    def _build_ui(self):
        self.configure(style="Card.TFrame")

        outer = tk.Frame(self, bg=BG_ELEVATED, highlightthickness=1,
                         highlightbackground=BORDER_COLOR)
        outer.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(outer, bg=BG_HEADER_LOG, cursor="fleur", height=32)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        accent_bar = tk.Frame(header, bg=ACCENT_BLUE, width=4)
        accent_bar.pack(side=tk.LEFT, fill=tk.Y)

        status_dot = tk.Label(header, text="●", fg=ACCENT_GREEN, bg=BG_HEADER_LOG,
                              font=("", 9))
        status_dot.pack(side=tk.LEFT, padx=(8, 4))

        icon_label = tk.Label(header, text="📄", bg=BG_HEADER_LOG, font=("", 10))
        icon_label.pack(side=tk.LEFT)

        fname = self._get_display_name()
        self._header_title = tk.Label(header, text=f" {fname}",
                                      fg=TEXT_PRIMARY, bg=BG_HEADER_LOG,
                                      font=("Microsoft YaHei UI", 9, "bold"),
                                      cursor="hand2")
        self._header_title.pack(side=tk.LEFT, padx=(2, 8))
        self._header_title.bind("<Double-Button-1>", self._start_title_edit)
        self._header_title.bind("<Enter>", lambda e: self._header_title.config(fg=ACCENT_BLUE))
        self._header_title.bind("<Leave>", lambda e: self._header_title.config(fg=TEXT_PRIMARY))
        self._title_edit_entry = None

        order_text = "新→旧" if self.order == "desc" else "旧→新"
        info_text = f"行数:{self.display_lines} | 刷新:{self.refresh_ms}ms | {order_text}"
        info_label = tk.Label(header, text=info_text, fg=TEXT_SECONDARY,
                              bg=BG_HEADER_LOG, font=("Microsoft YaHei UI", 8))
        info_label.pack(side=tk.LEFT)

        if not self._popup:
            detach_btn = tk.Label(header, text="⬈", fg=TEXT_SECONDARY,
                                  bg=BG_HEADER_LOG, cursor="hand2",
                                  font=("", 11))
            detach_btn.pack(side=tk.RIGHT, padx=(0, 8))
            detach_btn.bind("<Button-1>", lambda e: self._detach())
            detach_btn.bind("<Enter>", lambda e: detach_btn.config(fg=ACCENT_BLUE))
            detach_btn.bind("<Leave>", lambda e: detach_btn.config(fg=TEXT_SECONDARY))

        text_frame = tk.Frame(outer, bg=BG_ELEVATED)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=(0, 1))

        self.text_widget = tk.Text(
            text_frame,
            wrap=tk.NONE,
            state=tk.DISABLED,
            font=("Consolas", 10),
            bg=BG_DARK,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            borderwidth=0,
            highlightthickness=0,
            selectbackground=ACCENT_BLUE,
            selectforeground="#ffffff",
            padx=8,
            pady=6,
        )
        v_scrollbar = ttk.Scrollbar(
            text_frame, orient=tk.VERTICAL, command=self.text_widget.yview
        )
        h_scrollbar = ttk.Scrollbar(
            text_frame, orient=tk.HORIZONTAL, command=self.text_widget.xview
        )
        self.text_widget.configure(
            yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set
        )

        self.text_widget.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self._resize_grip = tk.Label(outer, text="◢", cursor="size_nw_se",
                                     font=("", 8), fg=TEXT_SECONDARY,
                                     bg=BG_ELEVATED)
        self._resize_grip.place(relx=1.0, rely=1.0, anchor="se")

        self._info_frame = header

    def _get_display_name(self):
        return self._config_item.get("display_name") or os.path.basename(self.log_path)

    def _start_title_edit(self, event=None):
        if self._title_edit_entry is not None:
            return
        current = self._header_title.cget("text").strip()
        self._title_edit_entry = tk.Entry(
            self._info_frame,
            font=("Microsoft YaHei UI", 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_HEADER_LOG,
            insertbackground=TEXT_PRIMARY,
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
            width=len(current) + 2,
        )
        self._title_edit_entry.insert(0, current)
        x, y = self._header_title.winfo_x(), self._header_title.winfo_y()
        self._header_title.pack_forget()
        self._title_edit_entry.place(x=x, y=y + 2, height=22)
        self._title_edit_entry.focus_set()
        self._title_edit_entry.select_range(0, tk.END)
        self._title_edit_entry.bind("<Return>", self._finish_title_edit)
        self._title_edit_entry.bind("<FocusOut>", self._finish_title_edit)
        self._title_edit_entry.bind("<Escape>", self._cancel_title_edit)

    def _finish_title_edit(self, event=None):
        if self._title_edit_entry is None:
            return
        new_name = self._title_edit_entry.get().strip()
        self._title_edit_entry.destroy()
        self._title_edit_entry = None

        if not new_name:
            new_name = os.path.basename(self.log_path)
            self._config_item.pop("display_name", None)
        else:
            current_display = self._config_item.get("display_name")
            if new_name == os.path.basename(self.log_path):
                self._config_item.pop("display_name", None)
            elif new_name != current_display:
                self._config_item["display_name"] = new_name

        self._header_title.config(text=f" {new_name}")
        self._header_title.pack(side=tk.LEFT, padx=(2, 8), before=self._info_frame.winfo_children()[4])
        if self._on_config_change:
            self._on_config_change()
        if self._toplevel is not None:
            self._toplevel.title(new_name)

    def _cancel_title_edit(self, event=None):
        if self._title_edit_entry is None:
            return
        self._title_edit_entry.destroy()
        self._title_edit_entry = None
        current = self._get_display_name()
        self._header_title.config(text=f" {current}")
        self._header_title.pack(side=tk.LEFT, padx=(2, 8), before=self._info_frame.winfo_children()[4])

    def enable_drag_resize(self, content_parent):
        self._content_parent = content_parent
        self._drag_data = {"x": 0, "y": 0}
        self._resize_data = {"x": 0, "y": 0, "w": 0, "h": 0}

        self._info_frame.bind("<ButtonPress-1>", self._start_drag)
        self._info_frame.bind("<B1-Motion>", self._on_drag)
        self._info_frame.bind("<ButtonRelease-1>", self._stop_drag)

        self._resize_grip.bind("<ButtonPress-1>", self._start_resize)
        self._resize_grip.bind("<B1-Motion>", self._on_resize)
        self._resize_grip.bind("<ButtonRelease-1>", self._stop_resize)

        for child in self._info_frame.winfo_children():
            if isinstance(child, tk.Label) and child.cget("text") in ("⬈",):
                continue
            child.bind("<ButtonPress-1>", self._start_drag)
            child.bind("<B1-Motion>", self._on_drag)
            child.bind("<ButtonRelease-1>", self._stop_drag)

    def _start_drag(self, event):
        self._drag_data["x"] = event.x_root
        self._drag_data["y"] = event.y_root
        self.lift()

    def _on_drag(self, event):
        dx = event.x_root - self._drag_data["x"]
        dy = event.y_root - self._drag_data["y"]
        self._drag_data["x"] = event.x_root
        self._drag_data["y"] = event.y_root

        new_x = self.winfo_x() + dx
        new_y = self.winfo_y() + dy
        self.place(x=new_x, y=new_y)
        self._save_place_geometry()

    def _stop_drag(self, event):
        self._save_place_geometry()

    def _start_resize(self, event):
        self._resize_data["x"] = event.x_root
        self._resize_data["y"] = event.y_root
        self._resize_data["w"] = self.winfo_width()
        self._resize_data["h"] = self.winfo_height()

    def _on_resize(self, event):
        dx = event.x_root - self._resize_data["x"]
        dy = event.y_root - self._resize_data["y"]
        new_w = max(200, self._resize_data["w"] + dx)
        new_h = max(150, self._resize_data["h"] + dy)
        self.place(width=new_w, height=new_h)
        self._save_place_geometry()

    def _stop_resize(self, event):
        self._save_place_geometry()

    def _save_place_geometry(self):
        try:
            self._config_item["x"] = self.winfo_x()
            self._config_item["y"] = self.winfo_y()
            self._config_item["width"] = self.winfo_width()
            self._config_item["height"] = self.winfo_height()
            if self._on_config_change:
                self._on_config_change()
        except Exception:
            pass

    def _schedule_refresh(self):
        if not self._active:
            return
        self._load_and_display()
        self.after(self.refresh_ms, self._schedule_refresh)

    def _load_and_display(self):
        content = self._read_last_lines()
        self.text_widget.configure(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", content)
        self.text_widget.configure(state=tk.DISABLED)

    def _read_last_lines(self):
        if not os.path.isfile(self.log_path):
            return f"[错误] 文件不存在: {self.log_path}"

        try:
            with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            selected = lines[-self.display_lines:]
            if self.order == "desc":
                selected.reverse()
            return "".join(selected)
        except Exception as e:
            return f"[错误] 读取文件失败: {e}"

    def _detach(self):
        if self._toplevel is not None:
            return
        self._save_place_geometry()
        self._config_item["detached"] = True
        if self._on_config_change:
            self._on_config_change()

        self.stop_refresh()
        self.place_forget()

        self._toplevel = tk.Toplevel(self.winfo_toplevel())
        self._toplevel.title(self._get_display_name())
        self._toplevel.protocol("WM_DELETE_WINDOW", self._reattach)

        self._detached_panel = LogPanel(
            self._toplevel, self._config_item, _popup=True
        )
        self._detached_panel.pack(fill=tk.BOTH, expand=True)

        geom = self._config_item.get("geometry", "500x350")
        self._toplevel.geometry(geom)

    def _reattach(self):
        if self._toplevel is None:
            return
        try:
            geom = self._toplevel.geometry()
            self._config_item["geometry"] = geom
        except Exception:
            pass

        self._detached_panel.stop_refresh()
        self._toplevel.destroy()
        self._toplevel = None
        self._detached_panel = None

        self._config_item["detached"] = False
        if self._on_config_change:
            self._on_config_change()

        x = self._config_item.get("x", 10)
        y = self._config_item.get("y", 10)
        w = self._config_item.get("width", 400)
        h = self._config_item.get("height", 300)
        self.place(x=x, y=y, width=w, height=h)
        self.lift()
        self._active = True
        self._schedule_refresh()

    @property
    def is_detached(self):
        return self._toplevel is not None