import csv
import os
import tkinter as tk
from tkinter import messagebox, ttk


class TablePanel(ttk.Frame):
    def __init__(self, parent, config_item, on_config_change=None, _popup=False):
        super().__init__(parent)
        self.csv_path = config_item["path"]
        self.max_rows = config_item["max_rows"]
        self.refresh_ms = config_item["refresh_ms"]
        self.columns = config_item.get("columns", [])
        self.column_aliases = config_item.get("column_aliases", {})
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

        ttk.Label(self._info_frame, text=f"CSV: {self.csv_path}").pack(side=tk.LEFT)
        ttk.Label(
            self._info_frame,
            text=f"列: {len(self.columns)}  |  行数: {self.max_rows}  |  刷新: {self.refresh_ms}ms",
        ).pack(side=tk.LEFT, padx=(8, 8))
        if not self._popup:
            ttk.Button(self._info_frame, text="弹出", command=self._detach, width=4).pack(
                side=tk.RIGHT
            )

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._tree = ttk.Treeview(tree_frame, show="headings", selectmode="browse")
        v_scrollbar = ttk.Scrollbar(
            tree_frame, orient=tk.VERTICAL, command=self._tree.yview
        )
        h_scrollbar = ttk.Scrollbar(
            tree_frame, orient=tk.HORIZONTAL, command=self._tree.xview
        )
        self._tree.configure(
            yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set
        )

        self._tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self._resize_grip = ttk.Label(self, text="◢", cursor="size_nw_se", font=("", 8))
        self._resize_grip.place(relx=1.0, rely=1.0, anchor="se")

        self._display_columns = []
        self._error_label = None

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
        all_columns, column_indices, rows, error = self._read_csv()
        if error:
            self._show_error(error)
            return

        self._clear_error()

        selected = self.columns if self.columns else all_columns

        display_columns = []
        for col in selected:
            alias = self.column_aliases.get(col, col)
            display_columns.append(alias)

        if display_columns != self._display_columns:
            self._tree["columns"] = display_columns
            for col_name, display_name in zip(selected, display_columns):
                self._tree.heading(display_name, text=display_name)
                self._tree.column(display_name, width=100, minwidth=50, stretch=True)
            self._display_columns = display_columns

        self._tree.delete(*self._tree.get_children())
        for row in rows:
            filtered = []
            for col in selected:
                idx = column_indices.get(col)
                if idx is not None and idx < len(row):
                    filtered.append(row[idx])
                else:
                    filtered.append("")
            self._tree.insert("", tk.END, values=filtered)

    def _read_csv(self):
        if not os.path.isfile(self.csv_path):
            return None, None, None, f"[错误] 文件不存在: {self.csv_path}"

        try:
            with open(self.csv_path, "r", encoding="utf-8", errors="replace", newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header is None:
                    return None, None, None, "[错误] CSV 文件为空"

                all_columns = [col.strip() or f"列{i + 1}" for i, col in enumerate(header)]
                column_indices = {col: i for i, col in enumerate(all_columns)}

                rows = []
                for row in reader:
                    if len(rows) >= self.max_rows:
                        break
                    rows.append(row)
                return all_columns, column_indices, rows, None
        except Exception as e:
            return None, None, None, f"[错误] 读取 CSV 失败: {e}"

    def _show_error(self, error):
        self._clear_error()
        self._tree.delete(*self._tree.get_children())
        self._error_label = ttk.Label(self._tree, text=error, foreground="red")
        self._error_label.place(relx=0.5, rely=0.5, anchor="center")

    def _clear_error(self):
        if self._error_label is not None:
            self._error_label.destroy()
            self._error_label = None

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
        self._toplevel.title(os.path.basename(self.csv_path))
        self._toplevel.protocol("WM_DELETE_WINDOW", self._reattach)

        self._detached_panel = TablePanel(
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


class _CsvColumnPickerDialog(tk.Toplevel):
    def __init__(self, parent, csv_path, available_columns, existing_columns=None,
                 existing_aliases=None, existing_max_rows=None, existing_refresh_ms=None):
        super().__init__(parent)
        self.title("选择CSV列")
        self.resizable(False, False)
        self.result = None
        self._columns = available_columns
        self._aliases = dict(existing_aliases) if existing_aliases else {}

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"CSV: {csv_path}").pack(anchor="w", pady=(0, 4))
        ttk.Label(
            frame,
            text="选择要显示的列，双击列名可设置别名:",
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

        for col in available_columns:
            alias = self._aliases.get(col, "")
            display = f"{col}  [{alias}]" if alias else col
            self.listbox.insert(tk.END, display)

        if existing_columns:
            for i, col in enumerate(available_columns):
                if col in existing_columns:
                    self.listbox.selection_set(i)

        self.listbox.bind("<<ListboxSelect>>", self._on_selection_change)
        self.listbox.bind("<Double-Button-1>", self._on_double_click)

        ttk.Label(frame, text="最大显示行数:").pack(anchor="w", pady=(8, 2))
        self.max_rows_var = tk.IntVar(value=existing_max_rows if existing_max_rows else 100)
        ttk.Spinbox(
            frame,
            from_=1,
            to=99999,
            textvariable=self.max_rows_var,
            width=12,
        ).pack(anchor="w")

        ttk.Label(frame, text="刷新间隔(ms):").pack(anchor="w", pady=(8, 2))
        self.refresh_var = tk.IntVar(value=existing_refresh_ms if existing_refresh_ms else 1000)
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

        self._on_selection_change()

        self.transient(parent)
        self.grab_set()
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry("+%d+%d" % (x, y))

    def _on_selection_change(self, event=None):
        count = len(self.listbox.curselection())
        self._count_label.config(text=f"已选: {count}")

    def _on_double_click(self, event):
        idx = self.listbox.nearest(event.y)
        if idx < 0 or idx >= len(self._columns):
            return
        col = self._columns[idx]
        current_alias = self._aliases.get(col, "")

        alias_dialog = _AliasDialog(self, col, current_alias)
        self.wait_window(alias_dialog)

        if alias_dialog.result is not None:
            new_alias = alias_dialog.result.strip()
            if new_alias:
                self._aliases[col] = new_alias
            else:
                self._aliases.pop(col, None)
            display = f"{col}  [{new_alias}]" if new_alias else col
            self.listbox.delete(idx)
            self.listbox.insert(idx, display)

    def _on_confirm(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("提示", "请至少选择一列。")
            return
        self.result = {
            "columns": [self._columns[i] for i in selected],
            "column_aliases": self._aliases,
            "max_rows": self.max_rows_var.get(),
            "refresh_ms": self.refresh_var.get(),
        }
        self.destroy()


class _AliasDialog(tk.Toplevel):
    def __init__(self, parent, field_name, current_alias):
        super().__init__(parent)
        self.title("设置别名")
        self.resizable(False, False)
        self.result = None

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"列名: {field_name}").pack(anchor="w", pady=(0, 6))
        ttk.Label(frame, text="别名:").pack(anchor="w")
        self._entry = ttk.Entry(frame, width=30)
        self._entry.pack(fill=tk.X, pady=(2, 8))
        self._entry.insert(0, current_alias)
        self._entry.focus_set()
        self._entry.select_range(0, tk.END)

        ttk.Label(frame, text="留空则使用列原名", foreground="gray").pack(anchor="w")

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