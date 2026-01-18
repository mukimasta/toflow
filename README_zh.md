# ToFlow

<div align="center">

<img src="./docs/assets/logo.png" alt="ToFlow Logo" width="100%">

**Focus, Action, Growth. All inside your terminal.**

[![Python](https://img.shields.io/badge/Python-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![TUI Powered](https://img.shields.io/badge/Interface-TUI-purple.svg)](https://github.com/prompt-toolkit/python-prompt-toolkit)

[English](./README.md) | **简体中文**

---

<img src="./docs/assets/demo.gif" alt="ToFlow Demo" width="100%">

</div>

## 简介

**ToFlow** 是一个基于终端的**个人生产力系统**，核心围绕两个概念构建：**项目化结构**与**番茄钟**。它帮助你在管理复杂人生目标的同时，保持专注和有节奏的执行。

*   **项目化结构**：告别扁平的清单。通过 **Track (方向) -> Project (项目) -> Todo (行动)** 的层级体系，让每一件小事都归属于一个项目，服务于长期目标。
*   **番茄钟与心流**：使用 **Now 行动器**（内置番茄钟）屏蔽干扰。将“规划”和“执行”分开，保持心智清晰，进入深度工作状态。
*   **看见成长**：自动记录每一次专注。通过 **Timeline** 视图回顾你的行动轨迹，让每一份努力都有迹可循。

## 核心特性

| | |
|---|---|
| 🎯 **结构化人生** | 告别混乱。通过 Track -> Project -> Todo 体系，让每一项任务都有归属。 |
| ⏱️ **心流状态** | 内置 "Now" 极简番茄钟。无压力的开始，沉浸式的执行。 |
| 📅 **时间线回顾** | 所有的专注记录都会被自动保存。通过 Timeline 视图，按时间倒序回顾你的行动轨迹，让每一份努力都有迹可循。 |
| ⌨️ **全键盘操作** | 专为极客打造。高效键位，毫秒级响应，手指无需离开键盘即可掌控一切。 |
| 📥 **收集箱机制** | Box 作为 Idea 与 Todo 的缓冲区。捕捉灵感，稍后整理，保持心智清晰。 |

## 快速开始

ToFlow 基于 Python 开发，推荐使用 `uv` 进行构建和运行。

### 安装与运行

```bash
# 1. 克隆仓库
git clone https://github.com/mukii/toflow.git
cd toflow

# 2. 安装依赖 (使用 uv)
uv sync

# 3. 运行 ToFlow
uv run toflow

# 4. 添加 alias（可选）
echo 'alias toflow="cd [toflow directory] && uv run toflow"' >> [your shell rc file]
source [your shell rc file]
```

*首次运行会自动初始化数据库于 `~/.toflow/toflow.db`*

## 文档

ToFlow 包含完整的文档体系，帮助你从入门到精通。

- **[📖 理念篇](./docs/PHILOSOPHY_zh.md)**
  <br>为什么我们需要另一个 Todo App？深入了解 ToFlow 背后的设计哲学。

- **[🕹️ 用户手册](./docs/MANUAL_zh.md)**
  <br>包含完整的快捷键列表、界面导航图与核心工作流指南。

- **[🛠️ 工程实现文档](./docs/DEVELOPER_zh.md)**
  <br>系统架构、数据模型设计与代码贡献指南。

- **[📝 更新日志](./CHANGELOG.md)**
  <br>查看版本迭代与新功能。


---

<div align="center">
Made with ❤️ by Mukii

[MIT License](./LICENSE)
</div>
