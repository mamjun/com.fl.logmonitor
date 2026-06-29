import os
import tkinter as tk
from tkinter import ttk


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
        self._info_frame = ttk.Frame(self, cursor="fleur")
        self._info_frame.pack(fill=tk.X, padx=4, pady=(4, 0))

        order_text = "新→旧" if self.order == "desc" else "旧→新"
        ttk.Label(self._info_frame, text=f"文件: {self.log_path}").pack(side=tk.LEFT)
        ttk.Label(
            self._info_frame,
            text=f"行数: {self.display_lines}  |  刷新: {self.refresh_ms}ms  |  排序: {order_text}",
        ).pack(side=tk.LEFT, padx=(8, 8))
        if not self._popup:
            ttk.Button(self._info_frame, text="弹出", command=self._detach, width=4).pack(
                side=tk.RIGHT
            )

        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.text_widget = tk.Text(
            text_frame,
            wrap=tk.NONE,
            state=tk.DISABLED,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#d4d4d4",
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

        self._resize_grip = ttk.Label(self, text="◢", cursor="size_nw_se", font=("", 8))
        self._resize_grip.place(relx=1.0, rely=1.0, anchor="se")

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
            if isinstance(child, ttk.Button):
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
        self._toplevel.title(os.path.basename(self.log_path))
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