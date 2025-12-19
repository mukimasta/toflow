# MukiTodo

## 简介 / 理念

MukiTodo 是一个**个人行动与成长系统**，用于组织和管理个人的人生方向，目标，对应的项目以及想法。帮助个人在多方向、多兴趣、多项目并行的状态下保持清晰；帮助个体对人生轨道有更好的觉知，更好地在不同领域分配自己的精力，从而实现长期主义视角下的全面成长。

MukiTodo 试图解决三个重要问题：\
第一，把“我正在进行的方向”“我想做的很多事情”从脑子里搬出来，用清晰的结构进行组织和管理，避免混乱、遗忘和反复权衡带来的心理负担；\
第二，在大量项目和想法并存的情况下，帮助识别和选择“当前值得投入的事项”，通过进度与结构视角，避免在单一项目或想法上过度投入，从而忽略紧急、重要或更有长期价值的方向；\
第三，让项目与行动的推进产生反馈与收获，通过记录过程中的经验和反思，将“做过的事情”转化为长期有效的成长积累。

MukiTodo 最核心的结构是 Track -> Project -> Todo 框架，分别代表人生方向/领域，方向下的项目，以及项目对应的具体行动。

通过这一结构组织项目与行动之后，可以通过 Now 行动器来行动。Now 行动器通过算法，智能选取当前最需要完成的 Todo。除此之外，还提供了类似番茄钟的功能，可以控制工作时长，避免过度沉浸，保护精力与身体状态。在任务结束后记录 Takeaways，产出记录、反思和收获。

希望 MukiTodo 能帮助你为复杂人生理清结构，在有限精力中做真正有价值的行动！


## 功能设计及设计理念

### 1. Track -> Project -> Todo 结构

在现实中，我们要做的事情，也就是 Todo 天然存在不同尺度：有些是长期方向和投入领域，有些是阶段性要推进的工程，还有些只是临时的一步行动；它们的重要性，紧急性，你对其的意愿也有所不同，如果这些 Todo 放进一个或几个列表里，就会导致混乱与失衡。

MukiTodo 定义了一个清晰的结构来管理这一切：\
Track / 轨道 代表了人生的不同领域。这些领域是我们希望长期投入的，并且每一个 Track 都在我们的生命中占据重要的、不可分割的位置。这些领域是并行的，所以用 Track 来形容是十分贴切的。在现在，有一部分人过于重视生活中的某一个领域，却忽视了它可能希望投入的另一个领域，例如为了工作，牺牲了家庭与爱好。MukiTodo 定义了 Track，就是希望你可以对你的人生轨道有更好的觉知，更好地在不同领域分配自己的精力，从而实现长期的全面成长。\
Project / 项目 代表了在某一个领域内，你希望投入精力完成的一些项目。它可以是你想长期投入的一件事，比如“学习心理学”，也可以是短期，有截止日期的工作内容，比如“课程演讲”。MukiTodo 以 Project 命名，就是在 Todo 列表的功能上，增加“阶段”、“项目周期”的概念。你可以在一个 Track 中不断开启新的 Project，也可以标记完成和归档旧项目，而不是像 Todo List 那样长期悬挂。\
Todo / 行动 的概念很简单，就是某个项目下的具体行动列表，通常是原子化的，清晰的。在执行时既能专注于当下的一步，也始终知道这一步在为哪个项目、哪个人生轨道服务。

这样的 Track -> Project -> Todo 结构与现在待办清单的嵌套文件夹看起来有些类似。不过这套结构的目的不仅在于“归类”，更在于“命名”和“定义”。当一个东西被称为 Project 时，它隐含着开始、推进、结束的生命周期，是一个需要被阶段性确认、完成或终止的对象，而不是一个扁平的清单。与以 Todo 为基本单元的传统的嵌套结构不同，MukiTodo 把 Project 项目作为基本单位，这将注意力从繁琐的细节行动转向对整体投入与方向的思考。系统不仅记录单个行动的完成，更承认项目的阶段性完成，从而提供清晰的阶段性反馈，避免了传统待办清单中不断勾选 Todo 却缺乏推进感的停滞感受。

### 2. Box 收集箱

Track -> Project -> Todo 提供了一个结构性的项目及任务管理框架，它很好地将我们引导向长期主义的行动模式。但是生活中也有一些暂时性的，一次性的工作，例如“阅读朋友发的网页”，“寄一个包裹”。这符合最原始的 Todo 定义，将其放入Track -> Project -> Todo 结构只会徒增负担，完全没有必要。我们用 Box 收集箱的 Todo 栏收集这些事项，需要时可以归档至结构内的 Todo 层级。同时，生活中会有许多的想法，代表了想要探索的一个新项目，这放在 Todo 里显然不合适。我们用 Box 收集箱的 Idea 栏收集这些想法，需要时可以归档至结构内的 Project 层级。


### 3. Now 行动器

有了 Track -> Project -> Todo 结构和 Box 收集箱，我们已经将“我有哪些事要做”“我想做哪些事”组织和管理起来了，接下来，MukiTodo 提供了 Now 行动器作为执行具体任务的工具。

我在今年大量使用 [Flow](https://www.flow.app/) 这款番茄钟工具。它的真正亮点在于极简的设计哲学：它的界面只有一个计时界面和开始按钮。任务的开始和结束应该是完全无压力的，而不是选择和纠结。Now 行动器借鉴了 Flow 的设计哲学：无需纠结。

Now 行动器的核心功能之一：无需纠结，找到当下最值得做的事。

当下我要做什么？\
我们有了 Track -> Project -> Todo 结构，也有了 Box 收集箱。在如此繁多的事项中，我们如何找到 Now / 现在 我要做什么？\
首先我们可以进入结构或 Box 自行选择一项行动，没有哪个算法能够替代用户做决定。\
其次，在用户没有选择的情况下，为了达成无需纠结的理念，我们通过 Deadline、重要性、紧急程度、意愿为用户综合推荐一个 Now list。

Now 行动器的核心功能之二：提供极简的番茄钟的倒计时、正计时、休息时间，避免过度沉浸，保护精力与身体健康。\
如果说上面的架构都只是搭建基础，那这一步就是真正开始行动的地方。我们希望用户的每次行动，都能够不纠结，无压力，进入最好的心流状态，并在合适的时候退出。

Now 行动器的核心功能之三：Takeaways\

<!-- GPT -->
3.1 无需纠结：找到当下最值得推进的一步

在 MukiTodo 中，“当下最值得做的事”并不等同于“最紧急”“最重要”或“最想做”。这些维度在不同情境下都会失效。Now 行动器的设计理念是：在不破坏整体结构和平衡的前提下，选取一项最适合当前状态推进的一小步行动。

因此，Now 行动器并不是简单地对所有 Todo 排序，而是在结构已经确定的前提下，综合考虑多个因素，对候选行动进行筛选和权衡，例如：

是否存在明确的截止时间或外部约束；

该行动对当前 Project 推进的关键程度；

行动本身的规模是否适合当前的时间和精力状态；

用户当前对该行动的心理意愿和阻力；

某些项目是否已经长时间未被推进，需要被重新唤起。

这些因素不会形成一个“绝对最优解”，而是帮助系统给出一个当下合理的建议。Now 行动器的目标不是“替你规划人生”，而是让你在这一刻，可以毫不费力地开始。

3.2 行动本身应该是轻的

Now 行动器借鉴了 Flow 等极简番茄钟工具的设计理念：行动的开始和结束都应该是低摩擦的。

在 Now 中，你不需要再次思考结构、优先级或长期意义。你只需要面对一件具体、清晰的 Todo，并决定是否开始。计时、休息和退出的存在，并不是为了提高效率，而是为了帮助你：

避免在状态良好时无限延长投入，导致精力透支；

给行动一个自然的结束点，而不是被动中断；

让“推进一点点”成为一种可持续的节奏。

如果说 Track -> Project -> Todo 是理性层面的结构设计，那么 Now 行动器更接近于行为层面的支持工具：它尊重人的注意力有限、能量波动的现实。

3.3 Takeaways：让行动产生积累

在传统的待办清单中，任务完成往往意味着“被勾掉然后消失”。但在 MukiTodo 中，行动的结束并不是终点，而是一次内化的机会。

Now 行动器与 Takeaways 紧密结合。在一次行动结束后，用户可以记录：

这次推进中学到了什么；

哪些判断被验证或被修正；

哪些新的问题、想法或项目被激发出来。

这些 Takeaways 不只是日志，而是连接行动与长期成长的桥梁。它们可以反向生成新的 Idea、Project 或 Todo，也可以在未来帮助你更好地理解自己的节奏、偏好与限制。

通过 Takeaways，MukiTodo 将“做过的事情”转化为“留下来的东西”，让每一次行动，不论大小，都有机会成为长期积累的一部分。
<!--  -->

### 




## 界面与交互设计

### 1. Now 行动器


### 2. Track -> Project -> Todo 结构

General:
- Move Cursor: Up/Down Arrow
- Select: Right Arrow
- Back: Left Arrow
- Add: + / =
- Delete: Backspace
- Rename: R

Structure Level: Tracks

Structure Level: Tracks with Projects (Default)

```text
┌─ Track 1: Work ────────────────────┐
│  ▸ Project 1: Backend              │
│    Project 2: Frontend             │
└────────────────────────────────────┘

┌─ Track 2: Personal ────────────────┐
│    Project 1: Blog                 │
└────────────────────────────────────┘
```

Toggle View: T

Structure Level: Todos

Done/Undo Todo Item: Space


- 






### 3. Box 收集箱


### 



## 工程实现

### 项目结构

```
mukitodo/
├── pyproject.toml          # uv 项目配置与依赖
├── README.md
├── mukitodo/
│   ├── __init__.py
│   ├── cli.py              # Typer 命令行入口 (todo 命令)
│   ├── commands.py         # 命令解析与执行（无状态）
│   ├── domain.py           # 业务对象与规则（不涉及数据库）
│   ├── models.py           # SQLAlchemy/SQLite ORM 模型
│   ├── database.py         # 数据库连接与初始化
│   ├── services.py         # 协调层（连接 domain 和 models）
│   └── tui/                # prompt-toolkit TUI 应用
│       ├── __init__.py
│       ├── state.py        # 状态管理
│       ├── render.py       # 渲染函数
│       └── app.py          # 按键绑定 + 启动入口
```

代码风格：自解释，减少不必要的注释


### 环境管理 (uv)

使用 uv 进行依赖管理，pyproject.toml 配置 `[project.scripts]` 使 `todo` 命令可用。

### 数据存储

SQLite 数据库，路径：`~/.mukitodo/todo.db`

数据库设计：

Track:
- id PRIMARY KEY
- name NOT NULL
- description
- status NOT NULL, DEFAULT 'active' (active / sleeping / archived)
- created_at NOT NULL
- archived_at
- order_index

Project:
- id PRIMARY KEY
- track_id NOT NULL, FOREIGN KEY REFERENCES Track(id)
- name NOT NULL
- description
- status NOT NULL, DEFAULT 'active' (active / focusing / sleeping / finished / archived)
- created_at NOT NULL
- started_at
- finished_at
- archived_at
- order_index

TodoItem: (Structure Todo / Box Todo)
- id PRIMARY KEY
- project_id FOREIGN KEY REFERENCES Project(id) (nullable)
- title NOT NULL
- description
- status NOT NULL, DEFAULT 'active' (active / sleeping / finished / archived)
- created_at NOT NULL
- completed_at
- order_index


Idea:

Session: (Now Action Session)

Takeaway:








### CLI 命令 (typer)

```bash
# 可视化
todo view
todo                        # 默认进入 TUI
todo help
```
全局选项：`--no-view` 执行命令后不自动打开 TUI，命令待定

### TUI 界面 (prompt-toolkit)

```text
┌─ Track 1: Work ────────────────────┐
│  ▸ Project 1: Backend              │
│    Project 2: Frontend             │
└────────────────────────────────────┘

┌─ Track 2: Personal ────────────────┐
│    Project 1: Blog                 │
└────────────────────────────────────┘
```

- 主界面（Track & Project界面）：纵向显示 Track 及其 Project 层级视图，主界面不显示item
    - Track 用矩形方框显示，Track Name 显示在方框左上角：**Track <index>: <Track Name>**
    - Project 显示在对应 Track 的方框内：**Project <index>: <Project Name>**
    - 用不同颜色区分选中的Track和未选中的Track
- Projects 界面：
    - 纵向显示当前 Track 的 Projects，不显示Item：**Project <index>: <Project Name>**
- Items 界面：
    - 纵向显示当前 Project 的 Items：**Item <index>: <Item Content>**
- 退出：`Ctrl+C` / `Ctrl+D` / [`q`(提示是否退出，按 q 确认)]

**NORMAL MODE**

```bash
uparrow / w
    up (在 Track/Project/Item 之间移动)
downarrow / s
    down (在 Track/Project/Item 之间移动)
left / a
    left (进入上一级，例如从 Project 回到 Track)
right / d
    right (进入下一级，例如从 Track 进入 Project)
space （item界面）
    切换状态 undo/done
backspace / delete
    delete (删除当前选中的 Track/Project/Item，提示是否删除，再按一次 backspace/delete 确认删除)
+ / =
    add (添加 Track/Project/Item，直接在目标处空行，闪烁光标输入名称，按回车确认，ESC 取消)

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
delete <name> / <index>
select / enter <name> / <index>（或直接输入 <index>，相当于 NORMAL MODE 的进入下一级）
back （相当于 NORMAL MODE 的返回上一级）

# Item
done <name> / <index> （或直接输入 <index>）
undo <name> / <index> （或直接输入 <index>）
```


## 依赖

typer, prompt-toolkit, sqlalchemy
