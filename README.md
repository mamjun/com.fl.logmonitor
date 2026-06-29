# 日志监控器 (Log Monitor)

一个基于 Python tkinter 的实时日志与 JSON 数据监控工具，支持多列布局、可配置刷新频率。

## 环境要求

- Python 3.6+
- 标准库（tkinter, json, os），无需额外安装

## 快速开始

```bash
python log_monitor.py
```

也可指定自定义配置文件：

```bash
python log_monitor.py my_config.json
```

## 配置文件 (`config.json`)

```json
{
    "max_columns": 3,
    "json_max_columns": 3,
    "logs": [
        {
            "path": "example1.log",
            "lines": 30,
            "refresh_ms": 1000,
            "column": 1,
            "order": "asc"
        }
    ],
    "json_monitors": [
        {
            "path": "example.json",
            "fields": ["code", "data.host.hostname"],
            "refresh_ms": 1000,
            "column": 1
        }
    ]
}
```

### 全局配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_columns` | int | 3 | 日志监控行最大列数（1~10） |
| `json_max_columns` | int | 3 | JSON 监控行最大列数（1~10） |

### 日志监控项 (`logs`)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `path` | string | — | 日志文件路径（相对或绝对） |
| `lines` | int | — | 显示最后多少行 |
| `refresh_ms` | int | — | 刷新间隔（毫秒） |
| `column` | int | 1 | 所在列（1 ~ max_columns） |
| `order` | string | `"asc"` | 排序方向：`"asc"`（旧→新）/ `"desc"`（新→旧） |

### JSON 监控项 (`json_monitors`)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `path` | string | — | JSON 文件路径 |
| `fields` | list | — | 要监控的字段列表（最多 10 个），用点号分隔层级，如 `"data.host.hostname"` |
| `refresh_ms` | int | — | 刷新间隔（毫秒） |
| `column` | int | 1 | 所在列（1 ~ json_max_columns） |

## 界面操作

### 工具栏

| 按钮 | 功能 |
|------|------|
| **添加日志** | 选择日志文件 → 设置行数/刷新间隔/所在列/排序 → 写入配置 |
| **删除日志** | 列表中选择已监控的日志文件 → 删除 |
| **添加JSON** | 选择 JSON 文件 → 自动解析字段 → 多选最多 10 个字段 → 设置刷新间隔/所在列 → 写入配置 |
| **删除JSON** | 列表中选择已监控的 JSON 文件 → 删除 |
| **日志最大列数** | Spinbox，调整日志监控行的列数（1~10） |
| **JSON最大列数** | Spinbox，调整 JSON 监控行的列数（1~10） |

### 界面布局

```
┌────────────────────────────────────────────────┐
│  添加日志  删除日志  │  添加JSON  删除JSON  │ 日志最大列数:3  JSON最大列数:3 │
├────────────────────────────────────────────────┤
│  列1 (日志)        │  列2 (日志)        │  列3 (日志)        │
│  ┌──────────────┐  │  ┌──────────────┐  │                    │
│  │ example1.log │  │  │ example2.log │  │                    │
│  │              │  │  │              │  │                    │
│  └──────────────┘  │  └──────────────┘  │                    │
├────────────────────────────────────────────────┤
│  列1 (JSON)        │  列2 (JSON)        │  列3 (JSON)        │
│  ┌──────────────┐  │                    │                    │
│  │ example.json │  │                    │                    │
│  │ code: 0      │  │                    │                    │
│  │ hostname: .. │  │                    │                    │
│  └──────────────┘  │                    │                    │
└────────────────────────────────────────────────┘
```

- 同一列下有多个监控项时，以标签页（Tab）方式切换
- 日志面板和 JSON 面板之间用分隔线隔开
- 暗色主题（黑底浅色字）显示

## 文件说明

| 文件 | 说明 |
|------|------|
| `log_monitor.py` | 主程序 |
| `config.json` | 配置文件 |
| `example1.log` | 示例日志文件 |
| `example2.log` | 示例日志文件 |
| `example.json` | 示例 JSON 数据文件 |