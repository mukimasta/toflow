# MukiTodo 命令行 Todo 应用

## 项目结构

```
mukitodo/
├── pyproject.toml          # uv 项目配置与依赖
├── README.md
├── mukitodo/
│   ├── __init__.py
│   ├── cli.py              # Typer 命令行入口 (todo 命令)
│   ├── commands.py         # 命令执行器
│   ├── domain.py           # 业务对象与规则（不涉及数据库）
│   ├── models.py           # SQLAlchemy/SQLite ORM 模型
│   ├── database.py         # 数据库连接与初始化
│   ├── services.py         # 协调层（连接 domain 和 models）
│   └── view.py             # prompt-toolkit TUI 应用
```

代码风格：自解释，减少不必要的注释

## 环境管理 (uv)

使用 uv 进行依赖管理，pyproject.toml 配置 `[project.scripts]` 使 `todo` 命令可用。

## 数据存储

SQLite 数据库，路径：`~/.mukitodo/todo.db`

## CLI 命令 (typer)

```bash
# 可视化
todo view
todo                        # 默认进入 TUI
todo help
```
全局选项：`--no-view` 执行命令后不自动打开 TUI，命令待定

## TUI 界面 (prompt-toolkit)

- 纵向显示 Track 及其 Project 层级视图，主界面不显示item，进入project显示单个project及其items（无底部命令输入框）
- 退出：`Ctrl+C` / `Ctrl+D`

**NORMAL MODE**

```bash
uparrow / w
    up (在 Track/Project/Item 之间移动)
downarrow / s
    down (在 Track/Project/Item 之间移动)
left / a / [
    left (进入上一级，例如从 Project 回到 Track)
right / d / ]
    right (进入下一级，例如从 Track 进入 Project)
space （item界面）
    切换状态 undo/done

> / :
    进入命令模式 COMMAND MODE
```

**COMMAND MODE**

- 底部命令输入框，支持直接输入命令（无需 todo 前缀）
- 状态栏显示操作结果（绿色成功/红色失败）

```bash
# 退出命令模式
q / Ctrl+G / ESC

# help
help / h / ?

# Track / Project / Item (作用于当前选中层级)
add <name>
list
delete <name>
select <name> / enter <name>（相当于 NORMAL MODE 的进入下一级）
back （相当于 NORMAL MODE 的返回上一级）

# Item
done <name> / <index>
undo <name> / <index>
```


## 依赖

typer, prompt-toolkit, sqlalchemy
