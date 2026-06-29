import json
import os
import sys
import tkinter as tk
from tkinter import ttk


class LogPanel(ttk.Frame):
    def __init__(self, parent, config_item):
        super().__init__(parent)
        self.log_path = config_item["path"]
        self.display_lines = config_item["lines"]
        self.refresh_ms = config_item["refresh_ms"]

        self._build_ui()
        self._schedule_refresh()

    def _build_ui(self):
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, padx=4, pady=(4, 0))

        ttk.Label(info_frame, text=f"文件: {self.log_path}").pack(side=tk.LEFT)
        ttk.Label(
            info_frame,
            text=f"行数: {self.display_lines}  |  刷新: {self.refresh_ms}ms",
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
        self._load_and_display()
        self.after(self.refresh_ms, self._schedule_refresh)

    def _load_and_display(self):
        content = self._read_last_lines(self.log_path, self.display_lines)
        self.text_widget.configure(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", content)
        self.text_widget.configure(state=tk.DISABLED)

    @staticmethod
    def _read_last_lines(file_path, line_count):
        if not os.path.isfile(file_path):
            return f"[错误] 文件不存在: {file_path}"

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return "".join(lines[-line_count:])
        except Exception as e:
            return f"[错误] 读取文件失败: {e}"


class LogMonitorApp:
    def __init__(self, config_path="config.json"):
        self.root = tk.Tk()
        self.root.title("日志监控器")
        self.root.geometry("1000x600")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.panels = []
        self._load_config(config_path)

        if not self.panels:
            ttk.Label(
                self.root,
                text="配置文件中没有有效的日志配置项。",
                font=("", 12),
            ).pack(padx=20, pady=40)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_config(self, config_path):
        if not os.path.isfile(config_path):
            print(f"配置文件不存在: {config_path}")
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"配置文件解析失败: {e}")
            return

        for item in config.get("logs", []):
            path = item.get("path", "")
            lines = item.get("lines", 50)
            refresh_ms = item.get("refresh_ms", 1000)

            if not path:
                print(f"跳过缺少 path 的配置项: {item}")
                continue

            panel = LogPanel(
                self.notebook,
                {"path": path, "lines": lines, "refresh_ms": refresh_ms},
            )
            tab_name = os.path.basename(path) or path
            self.notebook.add(panel, text=tab_name)
            self.panels.append(panel)

    def _on_close(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    app = LogMonitorApp(config_path)
    app.run()


if __name__ == "__main__":
    main()