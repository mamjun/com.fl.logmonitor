import json
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from log_panel import LogPanel
from json_panel import JsonPanel, MAX_JSON_FIELDS, _FieldPickerDialog, _AliasDialog

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