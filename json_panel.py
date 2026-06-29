import json
import os
import tkinter as tk
from tkinter import messagebox, ttk

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