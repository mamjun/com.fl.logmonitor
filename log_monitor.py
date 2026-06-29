import json
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class LogPanel(ttk.Frame):
    def __init__(self, parent, config_item):
        super().__init__(parent)
        self.log_path = config_item["path"]
        self.display_lines = config_item["lines"]
        self.refresh_ms = config_item["refresh_ms"]
        self.order = config_item.get("order", "asc")
        self._active = True

        self._build_ui()
        self._schedule_refresh()

    def stop_refresh(self):
        self._active = False

    def _build_ui(self):
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, padx=4, pady=(4, 0))

        order_text = "新→旧" if self.order == "desc" else "旧→新"
        ttk.Label(info_frame, text=f"文件: {self.log_path}").pack(side=tk.LEFT)
        ttk.Label(
            info_frame,
            text=f"行数: {self.display_lines}  |  刷新: {self.refresh_ms}ms  |  排序: {order_text}",
        ).pack(side=tk.RIGHT)

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


MAX_JSON_FIELDS = 10


class JsonPanel(ttk.Frame):
    def __init__(self, parent, config_item):
        super().__init__(parent)
        self.json_path = config_item["path"]
        self.fields = config_item["fields"]
        self.refresh_ms = config_item["refresh_ms"]
        self._active = True

        self._build_ui()
        self._schedule_refresh()

    def stop_refresh(self):
        self._active = False

    def _build_ui(self):
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, padx=4, pady=(4, 0))

        ttk.Label(info_frame, text=f"JSON: {self.json_path}").pack(side=tk.LEFT)
        ttk.Label(
            info_frame,
            text=f"字段: {len(self.fields)}  |  刷新: {self.refresh_ms}ms",
        ).pack(side=tk.RIGHT)

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
            if value is None:
                lines.append(f"{field}: 数据获取失败")
            elif isinstance(value, (list, dict)):
                lines.append(f"{field}: {json.dumps(value, ensure_ascii=False)}")
            else:
                lines.append(f"{field}: {value}")
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


class LogMonitorApp:
    def __init__(self, config_path="config.json"):
        self.root = tk.Tk()
        self.root.title("日志监控器")
        self.root.geometry("1200x800")

        self.config_path = config_path
        self.max_columns = 3
        self.json_max_columns = 3
        self.panels = []
        self.json_panels = []
        self._log_frame = None
        self._json_frame = None
        self._separator = None
        self._paned = None
        self._empty_label = None

        self._load_max_columns()
        self._build_toolbar()
        self._reload()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_max_columns(self):
        config = self._read_config()
        if config is not None:
            self.max_columns = max(1, min(10, config.get("max_columns", 3)))
            self.json_max_columns = max(1, min(10, config.get("json_max_columns", 3)))

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
        ttk.Button(toolbar, text="删除JSON", command=self._delete_json).pack(
            side=tk.LEFT
        )
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Label(toolbar, text="日志最大列数:").pack(side=tk.LEFT, padx=(4, 2))
        self._max_col_var = tk.IntVar(value=self.max_columns)
        ttk.Spinbox(
            toolbar,
            from_=1,
            to=10,
            width=4,
            textvariable=self._max_col_var,
            command=self._on_max_columns_changed,
        ).pack(side=tk.LEFT)
        ttk.Label(toolbar, text="JSON最大列数:").pack(side=tk.LEFT, padx=(8, 2))
        self._json_max_col_var = tk.IntVar(value=self.json_max_columns)
        ttk.Spinbox(
            toolbar,
            from_=1,
            to=10,
            width=4,
            textvariable=self._json_max_col_var,
            command=self._on_json_max_columns_changed,
        ).pack(side=tk.LEFT)

    def _on_max_columns_changed(self):
        new_val = self._max_col_var.get()
        if new_val == self.max_columns:
            return
        self.max_columns = new_val
        config = self._read_config()
        if config is not None:
            config["max_columns"] = new_val
            self._write_config(config)
        self._reload()

    def _on_json_max_columns_changed(self):
        new_val = self._json_max_col_var.get()
        if new_val == self.json_max_columns:
            return
        self.json_max_columns = new_val
        config = self._read_config()
        if config is not None:
            config["json_max_columns"] = new_val
            self._write_config(config)
        self._reload()

    def _clear_panels(self):
        for panel in self.panels:
            panel.stop_refresh()
        self.panels.clear()

        for panel in self.json_panels:
            panel.stop_refresh()
        self.json_panels.clear()

        if self._log_frame is not None:
            self._log_frame.destroy()
            self._log_frame = None

        if self._json_frame is not None:
            self._json_frame.destroy()
            self._json_frame = None

        if self._separator is not None:
            self._separator.destroy()
            self._separator = None

        if self._paned is not None:
            self._paned.destroy()
            self._paned = None

        if self._empty_label is not None:
            self._empty_label.destroy()
            self._empty_label = None

    def _reload(self):
        self._clear_panels()

        config = self._read_config()
        if config is None:
            return

        log_items = config.get("logs", [])
        json_items = config.get("json_monitors", [])

        has_logs = bool(log_items)
        has_json = bool(json_items)

        if not has_logs and not has_json:
            self._empty_label = ttk.Label(
                self.root,
                text="配置文件中没有有效的监控项。",
                font=("", 12),
            )
            self._empty_label.pack(padx=20, pady=40)
            return

        if has_json and has_logs:
            self._paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
            self._paned.pack(fill=tk.BOTH, expand=True)

            self._build_json_section(json_items, self._paned)
            self._build_log_section(log_items, self._paned)

            self._paned.add(self._json_frame, weight=1)
            self._paned.add(self._log_frame, weight=1)

            sash = config.get("sash_position", 0)
            if sash:
                self.root.after(10, lambda s=sash: self._paned.sashpos(0, s))
        elif has_json:
            self._build_json_section(json_items, self.root)
        elif has_logs:
            self._build_log_section(log_items, self.root)

    def _build_log_section(self, log_items, parent=None):
        if parent is None:
            parent = self.root
        columns = {c: [] for c in range(1, self.max_columns + 1)}
        for item in log_items:
            path = item.get("path", "")
            if not path:
                continue
            column = max(1, min(self.max_columns, int(item.get("column", 1))))
            columns[column].append(item)

        active_columns = [c for c in range(1, self.max_columns + 1) if columns[c]]
        if not active_columns:
            return

        self._log_frame = ttk.Frame(parent)
        self._log_frame.pack(fill=tk.BOTH, expand=True)

        for i, col_idx in enumerate(active_columns):
            self._log_frame.columnconfigure(i, weight=1, uniform="col")
            notebook = ttk.Notebook(self._log_frame)
            notebook.grid(row=0, column=i, sticky="nsew", padx=2, pady=2)

            for item in columns[col_idx]:
                panel = LogPanel(notebook, item)
                tab_name = os.path.basename(item["path"]) or item["path"]
                notebook.add(panel, text=tab_name)
                self.panels.append(panel)

        self._log_frame.rowconfigure(0, weight=1)

    def _build_json_section(self, json_items, parent=None):
        if parent is None:
            parent = self.root
        columns = {c: [] for c in range(1, self.json_max_columns + 1)}
        for item in json_items:
            path = item.get("path", "")
            if not path:
                continue
            column = max(1, min(self.json_max_columns, int(item.get("column", 1))))
            columns[column].append(item)

        active_columns = [c for c in range(1, self.json_max_columns + 1) if columns[c]]
        if not active_columns:
            return

        self._json_frame = ttk.Frame(parent)
        self._json_frame.pack(fill=tk.BOTH, expand=True)

        for i, col_idx in enumerate(active_columns):
            self._json_frame.columnconfigure(i, weight=1, uniform="col")
            notebook = ttk.Notebook(self._json_frame)
            notebook.grid(row=0, column=i, sticky="nsew", padx=2, pady=2)

            for item in columns[col_idx]:
                panel = JsonPanel(notebook, item)
                tab_name = os.path.basename(item["path"]) or item["path"]
                notebook.add(panel, text=tab_name)
                self.json_panels.append(panel)

        self._json_frame.rowconfigure(0, weight=1)

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

    def _add_file(self):
        file_path = filedialog.askopenfilename(
            title="选择日志文件",
            filetypes=[("日志文件", "*.log *.txt"), ("所有文件", "*.*")],
        )
        if not file_path:
            return

        dialog = _AddFileDialog(self.root, file_path, self.max_columns)
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
            existing["column"] = dialog.result["column"]
            existing["order"] = dialog.result["order"]
        else:
            logs.append(
                {
                    "path": file_path,
                    "lines": dialog.result["lines"],
                    "refresh_ms": dialog.result["refresh_ms"],
                    "column": dialog.result["column"],
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

        dialog = _FieldPickerDialog(self.root, file_path, available_fields, self.json_max_columns)
        self.root.wait_window(dialog)

        if not dialog.result:
            return

        config = self._read_config()
        if config is None:
            return

        json_monitors = config.setdefault("json_monitors", [])

        existing = next(
            (item for item in json_monitors if item.get("path") == file_path), None
        )
        if existing:
            existing["fields"] = dialog.result["fields"]
            existing["refresh_ms"] = dialog.result["refresh_ms"]
            existing["column"] = dialog.result["column"]
        else:
            json_monitors.append(
                {
                    "path": file_path,
                    "fields": dialog.result["fields"],
                    "refresh_ms": dialog.result["refresh_ms"],
                    "column": dialog.result["column"],
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
        if self._paned is not None:
            try:
                pos = self._paned.sashpos(0)
                config = self._read_config()
                if config is not None:
                    config["sash_position"] = pos
                    self._write_config(config)
            except Exception:
                pass
        self._clear_panels()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


class _AddFileDialog(tk.Toplevel):
    def __init__(self, parent, file_path, max_columns=3):
        super().__init__(parent)
        self.title("添加日志文件")
        self.resizable(False, False)
        self.result = None
        self._max_columns = max_columns

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

        ttk.Label(frame, text="所在列:").grid(row=3, column=0, sticky="w", pady=2)
        self.column_var = tk.IntVar(value=1)
        ttk.Spinbox(frame, from_=1, to=self._max_columns, textvariable=self.column_var, width=12).grid(
            row=3, column=1, sticky="w", pady=2, padx=(8, 0)
        )

        ttk.Label(frame, text="排序:").grid(row=4, column=0, sticky="w", pady=2)
        self._order_map = {"旧→新": "asc", "新→旧": "desc"}
        self._order_display = {v: k for k, v in self._order_map.items()}
        self.order_var = tk.StringVar(value=self._order_display["asc"])
        ttk.Combobox(
            frame,
            textvariable=self.order_var,
            values=list(self._order_map.keys()),
            state="readonly",
            width=10,
        ).grid(row=4, column=1, sticky="w", pady=2, padx=(8, 0))

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(12, 0))
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
            "column": self.column_var.get(),
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
            column = item.get("column", 1)
            self.listbox.insert(tk.END, f"[第{column}列] {path}")

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
    def __init__(self, parent, json_path, available_fields, max_columns=3):
        super().__init__(parent)
        self.title("选择JSON字段")
        self.result = None
        self._max_columns = max_columns

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"JSON: {json_path}").pack(anchor="w", pady=(0, 4))
        ttk.Label(
            frame,
            text=f"选择要监控的字段（最多 {MAX_JSON_FIELDS} 个）:",
        ).pack(anchor="w", pady=(0, 6))

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
            self.listbox.insert(tk.END, field)

        self.listbox.bind("<<ListboxSelect>>", self._on_selection_change)

        settings_frame = ttk.Frame(frame)
        settings_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Label(settings_frame, text="刷新间隔(ms):").pack(side=tk.LEFT)
        self.refresh_var = tk.IntVar(value=1000)
        ttk.Spinbox(
            settings_frame,
            from_=100,
            to=60000,
            increment=100,
            textvariable=self.refresh_var,
            width=10,
        ).pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(settings_frame, text="所在列:").pack(side=tk.LEFT)
        self.column_var = tk.IntVar(value=1)
        ttk.Spinbox(
            settings_frame,
            from_=1,
            to=self._max_columns,
            textvariable=self.column_var,
            width=5,
        ).pack(side=tk.LEFT, padx=(4, 0))

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

    def _on_confirm(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("提示", "请至少选择一个字段。")
            return
        self.result = {
            "fields": [self._fields[i] for i in selected],
            "refresh_ms": self.refresh_var.get(),
            "column": self.column_var.get(),
        }
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
            column = item.get("column", 1)
            self.listbox.insert(tk.END, f"[第{column}列] {path}")

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


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    app = LogMonitorApp(config_path)
    app.run()


if __name__ == "__main__":
    main()