import json
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


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


MAX_JSON_FIELDS = 10


class JsonPanel(ttk.Frame):
    def __init__(self, parent, config_item, on_config_change=None, _popup=False):
        super().__init__(parent)
        self.json_path = config_item["path"]
        self.fields = config_item["fields"]
        self.field_aliases = config_item.get("field_aliases", {})
        self.refresh_ms = config_item["refresh_ms"]
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

        ttk.Label(self._info_frame, text=f"JSON: {self.json_path}").pack(side=tk.LEFT)
        ttk.Label(
            self._info_frame,
            text=f"字段: {len(self.fields)}  |  刷新: {self.refresh_ms}ms",
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
        content = self._read_json_fields()
        self.text_widget.configure(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", content)
        self.text_widget.configure(state=tk.DISABLED)

    def _read_json_fields(self):
        if not os.path.isfile(self.json_path):
            return f"[错误] 文件不存在: {self.json_path}"

        try:
            with open(self.json_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except Exception as e:
            return f"[错误] JSON 解析失败: {e}"

        lines = []
        for field in self.fields:
            value = self._get_field_value(data, field)
            display_name = self.field_aliases.get(field, field)
            if value is None:
                lines.append(f"{display_name}: 数据获取失败")
            elif isinstance(value, (list, dict)):
                lines.append(f"{display_name}: {json.dumps(value, ensure_ascii=False)}")
            else:
                lines.append(f"{display_name}: {value}")
        return "\n".join(lines)

    @staticmethod
    def _get_field_value(data, field_path):
        current = data
        for part in field_path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

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
        self._toplevel.title(os.path.basename(self.json_path))
        self._toplevel.protocol("WM_DELETE_WINDOW", self._reattach)

        self._detached_panel = JsonPanel(
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


PANEL_DEFAULT_W = 400
PANEL_DEFAULT_H = 300
PANEL_GAP = 10


class LogMonitorApp:
    def __init__(self, config_path="config.json"):
        self.root = tk.Tk()
        self.root.title("日志监控器")
        self.root.geometry("1200x800")

        self.config_path = config_path
        self.panels = []
        self.json_panels = []
        self._content_frame = None
        self._empty_label = None

        self._build_toolbar()
        self._reload()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=4, pady=4)

        ttk.Button(toolbar, text="添加日志", command=self._add_file).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(toolbar, text="删除日志", command=self._delete_file).pack(
            side=tk.LEFT, padx=(0, 12)
        )
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Button(toolbar, text="添加JSON", command=self._add_json).pack(
            side=tk.LEFT, padx=(4, 4)
        )
        ttk.Button(toolbar, text="编辑JSON", command=self._edit_json).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(toolbar, text="删除JSON", command=self._delete_json).pack(
            side=tk.LEFT
        )
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Button(toolbar, text="重新载入", command=self._reload).pack(
            side=tk.LEFT, padx=4
        )

    def _clear_panels(self):
        for panel in self.panels:
            try:
                panel.stop_refresh()
                if panel._detached_panel is not None:
                    panel._detached_panel.stop_refresh()
                if panel._toplevel is not None:
                    panel._toplevel.destroy()
            except Exception:
                pass
        self.panels.clear()

        for panel in self.json_panels:
            try:
                panel.stop_refresh()
                if panel._detached_panel is not None:
                    panel._detached_panel.stop_refresh()
                if panel._toplevel is not None:
                    panel._toplevel.destroy()
            except Exception:
                pass
        self.json_panels.clear()

        if self._content_frame is not None:
            self._content_frame.destroy()
            self._content_frame = None

        if self._empty_label is not None:
            self._empty_label.destroy()
            self._empty_label = None

    def _compute_default_layout(self, count):
        positions = []
        cols = max(1, int(self.root.winfo_width() / (PANEL_DEFAULT_W + PANEL_GAP * 2)))
        for i in range(count):
            col = i % cols
            row = i // cols
            x = PANEL_GAP + col * (PANEL_DEFAULT_W + PANEL_GAP)
            y = PANEL_GAP + row * (PANEL_DEFAULT_H + PANEL_GAP)
            positions.append((x, y, PANEL_DEFAULT_W, PANEL_DEFAULT_H))
        return positions

    def _reload(self):
        self._clear_panels()

        config = self._read_config()
        if config is None:
            return

        log_items = config.get("logs", [])
        json_items = config.get("json_monitors", [])

        all_items = []
        for item in log_items:
            if item.get("path"):
                all_items.append(("log", item))
        for item in json_items:
            if item.get("path"):
                all_items.append(("json", item))

        if not all_items:
            self._empty_label = ttk.Label(
                self.root,
                text="配置文件中没有有效的监控项。",
                font=("", 12),
            )
            self._empty_label.pack(padx=20, pady=40)
            return

        self._content_frame = tk.Frame(self.root, bg="#d0d0d0")
        self._content_frame.pack(fill=tk.BOTH, expand=True)

        needs_layout = []
        for item_type, item in all_items:
            if item.get("detached"):
                continue
            has_geo = all(k in item for k in ("x", "y", "width", "height"))
            if not has_geo:
                needs_layout.append((item_type, item))
            else:
                self._place_panel(item_type, item, item["x"], item["y"], item["width"], item["height"])

        if needs_layout:
            defaults = self._compute_default_layout(len(needs_layout))
            for (item_type, item), (x, y, w, h) in zip(needs_layout, defaults):
                self._place_panel(item_type, item, x, y, w, h)

        for item_type, item in all_items:
            if item.get("detached"):
                if item_type == "log":
                    panel = LogPanel(self._content_frame, item, on_config_change=self._save_config)
                    panel.enable_drag_resize(self._content_frame)
                    panel.place(x=0, y=0, width=1, height=1)
                    panel.place_forget()
                    self.panels.append(panel)
                    self.root.after(100, panel._detach)
                else:
                    panel = JsonPanel(self._content_frame, item, on_config_change=self._save_config)
                    panel.enable_drag_resize(self._content_frame)
                    panel.place(x=0, y=0, width=1, height=1)
                    panel.place_forget()
                    self.json_panels.append(panel)
                    self.root.after(100, panel._detach)

    def _place_panel(self, item_type, item, x, y, w, h):
        if item_type == "log":
            panel = LogPanel(self._content_frame, item, on_config_change=self._save_config)
            panel.place(x=x, y=y, width=w, height=h)
            panel.enable_drag_resize(self._content_frame)
            self.panels.append(panel)
        else:
            panel = JsonPanel(self._content_frame, item, on_config_change=self._save_config)
            panel.place(x=x, y=y, width=w, height=h)
            panel.enable_drag_resize(self._content_frame)
            self.json_panels.append(panel)

    def _read_config(self):
        if not os.path.isfile(self.config_path):
            return {"logs": []}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            messagebox.showerror("配置错误", f"配置文件解析失败: {e}")
            return None

    def _write_config(self, config):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except OSError as e:
            messagebox.showerror("写入失败", f"无法写入配置文件: {e}")

    def _save_config(self):
        config = self._read_config()
        if config is not None:
            self._write_config(config)

    def _add_file(self):
        file_path = filedialog.askopenfilename(
            title="选择日志文件",
            filetypes=[("日志文件", "*.log *.txt"), ("所有文件", "*.*")],
        )
        if not file_path:
            return

        dialog = _AddFileDialog(self.root, file_path)
        self.root.wait_window(dialog)

        if not dialog.result:
            return

        config = self._read_config()
        if config is None:
            return

        logs = config.setdefault("logs", [])

        existing = next((item for item in logs if item.get("path") == file_path), None)
        if existing:
            existing["lines"] = dialog.result["lines"]
            existing["refresh_ms"] = dialog.result["refresh_ms"]
            existing["order"] = dialog.result["order"]
        else:
            logs.append(
                {
                    "path": file_path,
                    "lines": dialog.result["lines"],
                    "refresh_ms": dialog.result["refresh_ms"],
                    "order": dialog.result["order"],
                }
            )

        self._write_config(config)
        self._reload()

    def _delete_file(self):
        config = self._read_config()
        if config is None:
            return

        logs = config.get("logs", [])
        if not logs:
            messagebox.showinfo("提示", "当前没有监控的日志文件。")
            return

        dialog = _DeleteFileDialog(self.root, logs)
        self.root.wait_window(dialog)

        if dialog.result_index is None:
            return

        del logs[dialog.result_index]
        self._write_config(config)
        self._reload()

    def _add_json(self):
        file_path = filedialog.askopenfilename(
            title="选择JSON文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("错误", f"无法读取JSON文件: {e}")
            return

        available_fields = self._extract_fields(data)
        if not available_fields:
            messagebox.showinfo("提示", "JSON文件中没有可提取的字段。")
            return

        config = self._read_config()
        if config is None:
            return

        json_monitors = config.setdefault("json_monitors", [])
        existing = next(
            (item for item in json_monitors if item.get("path") == file_path), None
        )
        existing_aliases = existing.get("field_aliases", {}) if existing else None

        dialog = _FieldPickerDialog(self.root, file_path, available_fields, existing_aliases)
        self.root.wait_window(dialog)

        if not dialog.result:
            return

        if existing:
            existing["fields"] = dialog.result["fields"]
            existing["field_aliases"] = dialog.result["field_aliases"]
            existing["refresh_ms"] = dialog.result["refresh_ms"]
        else:
            json_monitors.append(
                {
                    "path": file_path,
                    "fields": dialog.result["fields"],
                    "field_aliases": dialog.result["field_aliases"],
                    "refresh_ms": dialog.result["refresh_ms"],
                }
            )

        self._write_config(config)
        self._reload()

    def _delete_json(self):
        config = self._read_config()
        if config is None:
            return

        json_monitors = config.get("json_monitors", [])
        if not json_monitors:
            messagebox.showinfo("提示", "当前没有监控的JSON文件。")
            return

        dialog = _DeleteJsonDialog(self.root, json_monitors)
        self.root.wait_window(dialog)

        if dialog.result_index is None:
            return

        del json_monitors[dialog.result_index]
        self._write_config(config)
        self._reload()

    def _edit_json(self):
        config = self._read_config()
        if config is None:
            return

        json_monitors = config.get("json_monitors", [])
        if not json_monitors:
            messagebox.showinfo("提示", "当前没有监控的JSON文件。")
            return

        dialog = _EditJsonDialog(self.root, json_monitors)
        self.root.wait_window(dialog)

        if dialog.result_index is None:
            return

        item = json_monitors[dialog.result_index]
        file_path = item["path"]

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("错误", f"无法读取JSON文件: {e}")
            return

        available_fields = self._extract_fields(data)
        if not available_fields:
            messagebox.showinfo("提示", "JSON文件中没有可提取的字段。")
            return

        existing_aliases = item.get("field_aliases", {})
        field_dialog = _FieldPickerDialog(self.root, file_path, available_fields, existing_aliases)
        self.root.wait_window(field_dialog)

        if not field_dialog.result:
            return

        item["fields"] = field_dialog.result["fields"]
        item["field_aliases"] = field_dialog.result["field_aliases"]
        item["refresh_ms"] = field_dialog.result["refresh_ms"]

        self._write_config(config)
        self._reload()

    @staticmethod
    def _extract_fields(data, prefix=""):
        fields = []
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    fields.extend(LogMonitorApp._extract_fields(value, full_key))
                else:
                    fields.append(full_key)
        return fields

    def _on_close(self):
        for panel in self.panels + self.json_panels:
            if panel._toplevel is not None:
                try:
                    geom = panel._toplevel.geometry()
                    panel._config_item["geometry"] = geom
                except Exception:
                    pass
            if panel._detached_panel is not None:
                try:
                    panel._detached_panel.stop_refresh()
                except Exception:
                    pass
        self._save_config()
        self._clear_panels()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


class _AddFileDialog(tk.Toplevel):
    def __init__(self, parent, file_path):
        super().__init__(parent)
        self.title("添加日志文件")
        self.resizable(False, False)
        self.result = None

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"文件: {file_path}").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        ttk.Label(frame, text="显示行数:").grid(row=1, column=0, sticky="w", pady=2)
        self.lines_var = tk.IntVar(value=50)
        ttk.Spinbox(frame, from_=1, to=9999, textvariable=self.lines_var, width=12).grid(
            row=1, column=1, sticky="w", pady=2, padx=(8, 0)
        )

        ttk.Label(frame, text="刷新间隔(ms):").grid(row=2, column=0, sticky="w", pady=2)
        self.refresh_var = tk.IntVar(value=1000)
        ttk.Spinbox(
            frame, from_=100, to=60000, increment=100, textvariable=self.refresh_var, width=12
        ).grid(row=2, column=1, sticky="w", pady=2, padx=(8, 0))

        ttk.Label(frame, text="排序:").grid(row=3, column=0, sticky="w", pady=2)
        self._order_map = {"旧→新": "asc", "新→旧": "desc"}
        self._order_display = {v: k for k, v in self._order_map.items()}
        self.order_var = tk.StringVar(value=self._order_display["asc"])
        ttk.Combobox(
            frame,
            textvariable=self.order_var,
            values=list(self._order_map.keys()),
            state="readonly",
            width=10,
        ).grid(row=3, column=1, sticky="w", pady=2, padx=(8, 0))

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btn_frame, text="确定", command=self._on_confirm).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT)

        self.transient(parent)
        self.grab_set()
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))

    def _on_confirm(self):
        self.result = {
            "lines": self.lines_var.get(),
            "refresh_ms": self.refresh_var.get(),
            "order": self._order_map[self.order_var.get()],
        }
        self.destroy()


class _DeleteFileDialog(tk.Toplevel):
    def __init__(self, parent, log_items):
        super().__init__(parent)
        self.title("删除日志文件")
        self.resizable(False, False)
        self.result_index = None

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="选择要删除的日志文件:").pack(anchor="w", pady=(0, 6))

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(list_frame, width=60, height=10)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for item in log_items:
            path = item.get("path", "")
            self.listbox.insert(tk.END, path)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(12, 0))
        ttk.Button(btn_frame, text="删除", command=self._on_delete).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT)

        self.transient(parent)
        self.grab_set()
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))

    def _on_delete(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个日志文件。")
            return
        self.result_index = selection[0]
        self.destroy()


class _FieldPickerDialog(tk.Toplevel):
    def __init__(self, parent, json_path, available_fields, existing_aliases=None):
        super().__init__(parent)
        self.title("选择JSON字段")
        self.result = None
        self._aliases = dict(existing_aliases) if existing_aliases else {}

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"JSON: {json_path}").pack(anchor="w", pady=(0, 4))
        hint_frame = ttk.Frame(frame)
        hint_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(
            hint_frame,
            text=f"选择要监控的字段（最多 {MAX_JSON_FIELDS} 个），双击字段可设置别名:",
        ).pack(side=tk.LEFT)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(
            list_frame, width=60, height=14, selectmode=tk.MULTIPLE
        )
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.listbox.yview
        )
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._fields = available_fields
        for field in available_fields:
            alias = self._aliases.get(field, "")
            display = f"{field}  [{alias}]" if alias else field
            self.listbox.insert(tk.END, display)

        self.listbox.bind("<<ListboxSelect>>", self._on_selection_change)
        self.listbox.bind("<Double-Button-1>", self._on_double_click)

        ttk.Label(frame, text="刷新间隔(ms):").pack(anchor="w", pady=(8, 2))
        self.refresh_var = tk.IntVar(value=1000)
        ttk.Spinbox(
            frame,
            from_=100,
            to=60000,
            increment=100,
            textvariable=self.refresh_var,
            width=10,
        ).pack(anchor="w")

        self._count_label = ttk.Label(frame, text="已选: 0")
        self._count_label.pack(anchor="w", pady=(4, 0))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(12, 0))
        ttk.Button(btn_frame, text="确定", command=self._on_confirm).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT)

        self.transient(parent)
        self.grab_set()
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry("+%d+%d" % (x, y))

    def _on_selection_change(self, event=None):
        selected = self.listbox.curselection()
        count = len(selected)
        self._count_label.config(text=f"已选: {count}")
        if count > MAX_JSON_FIELDS:
            self.listbox.selection_clear(selected[-1])
            self._count_label.config(text=f"已选: {MAX_JSON_FIELDS}（最多{MAX_JSON_FIELDS}个）")

    def _on_double_click(self, event):
        idx = self.listbox.nearest(event.y)
        if idx < 0 or idx >= len(self._fields):
            return
        field = self._fields[idx]
        current_alias = self._aliases.get(field, "")

        alias_dialog = _AliasDialog(self, field, current_alias)
        self.wait_window(alias_dialog)

        if alias_dialog.result is not None:
            new_alias = alias_dialog.result.strip()
            if new_alias:
                self._aliases[field] = new_alias
            else:
                self._aliases.pop(field, None)
            display = f"{field}  [{new_alias}]" if new_alias else field
            self.listbox.delete(idx)
            self.listbox.insert(idx, display)

    def _on_confirm(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("提示", "请至少选择一个字段。")
            return
        self.result = {
            "fields": [self._fields[i] for i in selected],
            "field_aliases": self._aliases,
            "refresh_ms": self.refresh_var.get(),
        }
        self.destroy()


class _AliasDialog(tk.Toplevel):
    def __init__(self, parent, field_name, current_alias):
        super().__init__(parent)
        self.title("设置字段别名")
        self.resizable(False, False)
        self.result = None

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"字段: {field_name}").pack(anchor="w", pady=(0, 6))
        ttk.Label(frame, text="别名:").pack(anchor="w")
        self._entry = ttk.Entry(frame, width=30)
        self._entry.pack(fill=tk.X, pady=(2, 8))
        self._entry.insert(0, current_alias)
        self._entry.focus_set()
        self._entry.select_range(0, tk.END)

        ttk.Label(frame, text="留空则使用字段原名", foreground="gray").pack(anchor="w")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(12, 0))
        ttk.Button(btn_frame, text="确定", command=self._on_confirm).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT)

        self.bind("<Return>", lambda e: self._on_confirm())
        self.bind("<Escape>", lambda e: self.destroy())

        self.transient(parent)
        self.grab_set()
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry("+%d+%d" % (x, y))

    def _on_confirm(self):
        self.result = self._entry.get()
        self.destroy()


class _DeleteJsonDialog(tk.Toplevel):
    def __init__(self, parent, json_items):
        super().__init__(parent)
        self.title("删除JSON监控")
        self.resizable(False, False)
        self.result_index = None

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="选择要删除的JSON监控:").pack(anchor="w", pady=(0, 6))

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(list_frame, width=60, height=10)
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.listbox.yview
        )
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for item in json_items:
            path = item.get("path", "")
            self.listbox.insert(tk.END, path)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(12, 0))
        ttk.Button(btn_frame, text="删除", command=self._on_delete).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT)

        self.transient(parent)
        self.grab_set()
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))

    def _on_delete(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个JSON监控。")
            return
        self.result_index = selection[0]
        self.destroy()


class _EditJsonDialog(tk.Toplevel):
    def __init__(self, parent, json_items):
        super().__init__(parent)
        self.title("编辑JSON监控")
        self.resizable(False, False)
        self.result_index = None

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="选择要编辑的JSON监控:").pack(anchor="w", pady=(0, 6))

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(list_frame, width=60, height=10)
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.listbox.yview
        )
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for item in json_items:
            path = item.get("path", "")
            fields = item.get("fields", [])
            alias_count = len(item.get("field_aliases", {}))
            display = f"{path}  (字段: {len(fields)}, 别名: {alias_count})"
            self.listbox.insert(tk.END, display)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(12, 0))
        ttk.Button(btn_frame, text="编辑", command=self._on_edit).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT)

        self.transient(parent)
        self.grab_set()
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))

    def _on_edit(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个JSON监控。")
            return
        self.result_index = selection[0]
        self.destroy()


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    app = LogMonitorApp(config_path)
    app.run()


if __name__ == "__main__":
    main()