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

Track -> Project -> Todo 提供了一个结构性的项目及任务管理框架，它很好地将我们引导向长期主义的行动模式。但是生活中也有一些暂时性的，一次性的工作，例如“阅读朋友发的网页”，“寄一个包裹”。这符合最原始的 Todo 定义，将其放入Track -> Project -> Todo 结构只会徒增负担，完全没有必要。我们用 Box 收集箱的 Todo 栏收集这些事项，需要时可以升级至结构内的 Todo 层级。同时，生活中会有许多的想法，代表了想要探索的一个新项目，这放在 Todo 里显然不合适。我们用 Box 收集箱的 Idea 栏收集这些想法，需要时可以升级至结构内的 Project 层级。


### 3. Now 行动器

有了 Track -> Project -> Todo 结构和 Box 收集箱，我们已经将“我有哪些事要做”“我想做哪些事”组织和管理起来了，接下来，MukiTodo 提供了 Now 行动器作为执行具体任务的工具。

我在今年大量使用 [Flow](https://www.flow.app/) 这款番茄钟工具。它的真正亮点在于极简的设计哲学：它的界面只有一个计时界面和开始按钮。任务的开始和结束应该是完全无压力的，而不是选择和纠结。Now 行动器借鉴了 Flow 的设计哲学：无需纠结。

**Now 行动器的核心功能之一：无需纠结，找到当下最值得做的事**

我们有了 Track -> Project -> Todo 结构，也有了 Box 收集箱。在如此繁多的事项中，我们如何找到：\
Now / 现在 我要做什么？

首先我们可以进入结构或 Box 自行选择一项行动，没有哪个算法能够替代用户做决定。\
其次，在用户没有选择的情况下，为了达成无需纠结的理念，我们通过 Deadline、重要性、紧急程度、意愿为用户综合推荐一个 Now list。

同时，你也可以在不选择任何事项的情况下，直接开始行动，在行动结束后记录 Done List 和 Takeaways。

**Now 行动器的核心功能之二：提供极简的番茄钟的倒计时、休息时间，避免过度沉浸，保护精力与身体健康**

如果说上面的架构都只是搭建基础，那这一步就是真正开始行动的地方。我们希望用户的每次行动，都能够不纠结，无压力，进入最好的心流状态，并在合适的时候退出。

计时、休息和退出的存在，并不是为了提高效率，而是为了帮助你：避免在状态良好时无限延长投入，导致精力透支，让“推进一点点”成为一种可持续的节奏。

**Now 行动器的核心功能之三：Takeaways – 让行动产生积累**

在传统的待办清单中，任务完成往往意味着“被勾掉然后消失”。但在 MukiTodo 中，行动的结束并不是终点，而是一次内化的机会。

Now 行动器与 Takeaways 紧密结合。在一次行动结束后，用户可以记录：
- 这次推进中学到了什么
- 哪些判断被验证或被修正
- 哪些新的问题、想法或项目被激发出来

这些 Takeaways 不只是日志，而是连接行动与长期成长的桥梁。它们可以让你直观地感受到每天的进步，也可以在未来帮助你更好地理解自己的节奏、偏好与限制。

通过 Takeaways，MukiTodo 将“做过的事情”转化为“留下来的东西”，让每一次行动，不论大小，都有机会成为长期积累的一部分。

**Now 行动器的核心功能之四：Timeline 时间线**

Timeline 时间线视图用于查看所有保存的 Session 和 Takeaways，按时间倒序排列。


### 4. Archive 归档

Archive 归档视图用于查看所有已归档的 Item，包括 Track, Project, Todo, Session, Takeaway, Idea。
Archive 语义：我暂时不处理/不想看到这个事项，但是我希望保留它，将来可能需要处理。

### 5. Timeline 时间线

Timeline 时间线视图用于查看所有已完成的 Session，包括 Session 的基本信息：项目名称、开始时间、持续时间、收获（Takeaways）等。
Timeline 语义：我想要回顾我过去做了什么，以及我从中收获了什么。





## TUI 界面与交互设计

典型路径：
1. 进入 Structure 结构视图
2. 选择 Track, Project (, Todo)
3. 添加至 NOW 行动器
4. 开始行动
5. 结束行动并记录 Takeaways




### 全局按键

- Switch View: `Tab` (Between NOW and STRUCTURE)
- Timeline View: `t`
- Box View: `b`
- Archive View: `A`
- Info View: `i`
- Quit: `q`


### 1. Now 行动器

```text
┌───────────────────── NOW ──────────────────────┐
│                                                │
│               --- Item Info ---                │
│                                                │
│                     25:00                      │
│                                                │
│                       ⏱                        │
└────────────────────────────────────────────────┘
```

Item Info:
- Default: `--- No Todo Selected ---`
- Selected: `track > project[ > todo]`


- Start / Pause / Resume: `Space`
- Reset: `r`
- Adjust: `+ / = / -`
- View Info: `i`
- Timeline View: `t`
- Add Done Item: `d`
- Finish Session: `Enter`

When Session is finished:
1. Ask for Saving Confirmation
2. Ask for Done List if no item is selected
3. Save Session
4. Ask for Takeaways
5. Save Takeaways
6. Return to NOW view


### 2. Timeline View

- Enter Timeline View: `t`
- Leave Timeline View: `Esc` / `t`
- Move Cursor: `Up/Down Arrow`
- View Info: `i`
- Add Takeaway: `+ / =`
- Edit Takeaway: `r`
- Delete: `Backspace`

```text
┌─ Timeline ─────────────────────┐
│  -- 2025-12-29 --              │
│                                │
│  ▸ 18:30 25m Session 1: ...    │
│      ├── 18:32 Takeaway 1: ... │
│      └── 18:45 Takeaway 2: ... │
│                                │
│  -- 2025-12-28 --              │
│                                │
│    16:00 45m Session 3: ...    │
│      └── 16:42 Takeaway 1: ... │
│                                │
│    Takeaway: [action] ...      │
│                                │
└────────────────────────────────┘
```

### 3. Track -> Project -> Todo 结构

General:
- Move Cursor: `Up/Down Arrow`
- Select: `Right Arrow`
- Back: `Left Arrow`
- View Info: `i`
- Add: `+ / =`
- Rename: `r`
- Delete: `Backspace`
- Done / Undo: `Space` (Done/Finish/Complete)
- Enter NOW with item: `Enter`
- Archive Item: `a`
- Sleep Item: `s`
- Cancel Item: `c` (For Project/Todo/Idea(Deprecate))
- Record Takeaways: `t`
- Pin Item: `p` (For Project/Todo)

Display Format:

`<status> <Type + index + name> <flags> <right-aligned: hints, ddl>`

- status: (according to the status of the item)
    - focusing: `📌` (bold line)
    - active：`○`
    - sleeping：`z` (dim line)
    - finished/done：`◉` (dim line)
    - cancelled：`×` (dim + strike line)
- Type + index + name: `Track/Project/Todo <index>: <name>`
- flags: 
    - has description: `[≡]`
    - has url: `[↗]` (only for Todo)
    - session：`[⧗k]` (k is the number) (Include count of children)
    - takeaway：`[✎k]` (k is the number) (Include count of children)
- Hints (only for Project) (Display when 2-3):
    - willingness: `♥`
    - importance: `⭑`
    - urgency: `⚡`
- Deadline: `YYYY-MM-DD` (Red date if past)

Example:
`📌 Project 1: Backend [≡] [⧗3] [✎1]      ♥ ⭑ ⚡ 2025-12-31`
`○ Todo 1: Buy Groceries [↗] [⧗1] [✎1]`

**Structure Level: Tracks**

Simple List.

**Structure Level: Tracks with Projects (Default)**

```text
┌─ Track 1: Work ────────────────────┐
│  ▸ Project 1: Backend              │
│    Project 2: Frontend             │
└────────────────────────────────────┘

┌─ Track 2: Personal ────────────────┐
│    Project 1: Blog                 │
└────────────────────────────────────┘
```


**Structure Level: Todos**

Simple List.

### 3. Info 详细信息

- Quit Info View: `i` / `Escape`
- Move Cursor: `Up/Down Arrow`
- Edit Field: `r`
- 


### 4. Box 收集箱
Box 视图用于收集「临时 Todo」和「新项目 Idea」，并提供一条从 Box 归入结构的无压力路径。

- Enter Box: `b`（from any view；进入默认落在 Box Todos）
- Switch Subview: `[` → Box Todos， `]` → Box Ideas
- Move Cursor: `↑/↓ Arrow`
- View Info: `i`
- Add: `+ / =`
- Edit: `r`
- Archive: `a`（二次确认）
- Delete: `Backspace`（二次确认）

**Box Todo → Move to Structure**

- Start Move: `m`（在 Box Todos 中）
- 进入 STRUCTURE 后会自动回到 `TRACKS_WITH_PROJECTS_T`（焦点在 Track）
- `→` 进入 Project 层（`TRACKS_WITH_PROJECTS_P`）
- `→` 进入 Todo 层（`TODOS`，cursor 为 None，不高亮），并直接进入 Confirm
- Confirm: `Enter`（二次确认）
- Cancel: `Esc`（在 Structure 中取消本次 Move，并回到 Box）

**Box Idea → Promote to Project**

- Start Promote: `p`（在 Box Ideas 中）
- 进入 STRUCTURE 后会自动回到 `TRACKS_WITH_PROJECTS_T`
- Confirm: `Enter`（二次确认）
- Promote 期间按 `→` 会直接进入 Confirm（不会进入 Project 层）
- 已经 `promoted` 的 idea 无法再次 promote（在 Box 和 actions 层均拦截）

### 5. Archive 归档

```text
┌─ Archive ──────────────────────┐
│  Archived Tracks               │
│                                │
│  ▸ Track: Project Mgmt         │
│      Project: Backend Design   │
│         ○ Setup Database       │
│         ✓ Write Schemas        │
│    Project: (finished)         │
│                                │
│  Track: Fitness                │
│      Project: Marathon Train   │
│                                │
│  Archived Box Todos            │
│                                │
│  ▸ Todo: Buy Groceries         │
│    Todo: Clean Up Office       │
│                                │
│  Archived Box Ideas            │
│                                │
│  ▸ Idea: AI Learning Path      │
│    Idea: Home Automation       │
│                                │
└────────────────────────────────┘
```

- Enter: `A` (from any view)
- Exit: `Esc` / `A`
- Move Cursor: `↑/↓ Arrow`
- View Info: `i` (进入 INFO View 查看详细信息)
- Unarchive Item: `u`


### Input Mode 输入模式

```text
(Input Purpose Prompt)  (Title / Name Input)        [Date Edit]
[Field Edit]  (Description / Content Input)
```

- Input Purpose Prompt: 
- 

例如：
```text
[New Project] Project: Update Resume  [Started 2025-12-01 | Deadline 2026-01-03]
[Focusing] [♥ ▂  ⭑ █  ⚡ ▅]  Update the resume for 2026 job application
```

- Switch Field: `Tab` / `Shift+Tab`
- Adjust Value: `Space` / `+` / `-` / `Up` / `Down`
- Input Content (Title/Description/Content): `Any`
- Cancel Input: `Escape` / `Ctrl+G`
- Confirm Input: `Enter`


▁ ▂ ▃ ▄ ▅ ▆ ▇ █






**COMMAND MODE**

- 底部命令输入框，支持直接输入命令（无需 todo 前缀）
- 状态栏显示操作结果（绿色成功/红色失败）

计划在未来实现


## CLI 命令设计（计划在未来实现）

Actions:

```bash
todo                        # Open TUI (default)
todo help                   # Show help
todo view                   # Open TUI

# Track Commands
todo create track <name> [<description>]        # Create a track
todo delete track <id>                          # Delete a track
todo list tracks                                # List all tracks (default: (id, name))
todo track <id>                                 # View track details
todo rename track <id> <new_name>               # Rename a track
todo update track --description <description>   # Update track description
todo activate track <id>                        # Activate a track
todo sleep track <id>                           # Sleep a track
todo archive track <id>                         # Archive a track
todo unarchive track <id>                       # Unarchive a track

# Project Commands
todo create project <name> in <track_id> [<description>]    # Create a project in a track
todo delete project <id>                                # Delete a project
todo list projects in <track_id>                         # List all projects in a track
todo project <id>                                       # View project details
todo rename project <id> <new_name>                      # Rename a project
todo update project --description <description>          # Update project properties
                    --deadline <deadline>
                    --willingness_hint <willingness_hint>
                    --importance_hint <importance_hint>
                    --urgency_hint <urgency_hint>
todo activate project <id>                               # Activate a project
todo focus project <id>                                  # Focus a project
todo sleep project <id>                                  # Sleep a project
todo cancel project <id>                                 # Cancel a project
todo finish project <id>                                 # Finish a project
todo archive project <id>                                # Archive a project
todo unarchive project <id>                              # Unarchive a project

# Todo Commands
todo create todo <name> in <project_id> [<description>]    # Create a todo in a project
todo delete todo <id>                                      # Delete a todo
todo list todos in <project_id>                             # List all todos in a project
todo todo <id>                                              # View todo details
todo rename todo <id> <new_name>                             # Rename a todo
todo update todo --description <description>                 # Update todo properties
                 --url <url>
                 --deadline <deadline>
todo activate todo <id>                                   # Activate a todo
todo done todo <id>                                        # Done a todo
todo cancel todo <id>                                      # Cancel a todo
todo archive todo <id>                                      # Archive a todo
todo unarchive todo <id>                                    # Unarchive a todo


# Box Commands
todo create box todo <name> [<description>]     # Create a box todo
todo delete box todo <id>                       # Delete a box todo
todo list box todos                             # List all box todos
todo box todo <id>                              # View box todo details
todo rename box todo <id> <new_name>            # Rename a box todo
todo update box todo --description <description>    # Update box todo properties
                     --url <url>
                     --deadline <deadline>
todo activate box todo <id>                       # Activate a box todo
todo done box todo <id>                            # Done a box todo
todo cancel box todo <id>                          # Cancel a box todo
todo archive box todo <id>                          # Archive a box todo
todo unarchive box todo <id>                        # Unarchive a box todo

todo create idea <name> [<description>]    # Create a idea
todo delete idea <id>                      # Delete a idea
todo list ideas                             # List all ideas
todo idea <id>                              # View idea details
todo rename idea <id> <new_name>            # Rename a idea
todo update idea --description <description> # Update idea properties
                    --maturity_hint <maturity_hint>
                    --willingness_hint <willingness_hint>
todo activate idea <id>                       # Activate a idea
todo sleep idea <id>                          # Sleep a idea
todo deprecate idea <id>                      # Deprecate a idea
todo promote idea <id> to <track_id>          # Promote a idea to a track
todo archive idea <id>                         # Archive a idea
todo unarchive idea <id>                       # Unarchive a idea

# Now Session Commands
# No real-time timer for CLI currently
todo save session <project_id> <todo_id> <duration_minutes> <started_at_utc> <ended_at_utc> [--takeaway <takeaway_content>] # Save a session and record takeaway
todo delete session <id>                          # Delete a session
todo list sessions                                # List all sessions
todo session <id>                                  # View session details

# Takeaway Commands
todo create takeaway <title> <content> [--project_id <project_id>] [--todo_id <todo_id>] [--session_id <session_id>] # Create a takeaway
todo delete takeaway <id>                          # Delete a takeaway
todo list takeaways                                # List all takeaways
todo takeaway <id>                                  # View takeaway details
todo update takeaway --title <title> --content <content>            # Update takeaway content
todo archive takeaway <id>                         # Archive a takeaway
todo unarchive takeaway <id>                       # Unarchive a takeaway
```



## 工程设计与实现

### 项目结构

```text
.
├── pyproject.toml          # uv environment management (project config)
├── README.md               # README documentation
├── CHANGELOG.md            # CHANGELOG documentation
├── main.py                 # Legacy entry point (optional)
├── mukitodo/
│   ├── __init__.py         # Package init
│   ├── cli.py              # CLI entry point ("todo" command)
│   ├── actions.py          # Business logic
│   ├── database.py         # Database connection & setup
│   ├── models.py           # SQLAlchemy ORM models
│   └── tui/                # prompt-toolkit Terminal UI Application
│       ├── __init__.py     # TUI package core
│       ├── app.py          # Key bindings, layout, TUI app launcher
│       ├── layout_manager.py    # Dynamic layout computation
│       ├── renderer.py     # Pure rendering routines
│       ├── states/         # State management modules
│       │   ├── app_state.py        # Top-level state coordinator
│       │   ├── input_state.py      # Input MODE state
│       │   ├── now_state.py        # NOW VIEW state
│       │   ├── structure_state.py  # STRUCTURE VIEW state
│       │   ├── info_state.py       # INFO VIEW state
│       │   ├── timeline_state.py   # TIMELINE VIEW state
│       │   ├── archive_state.py    # ARCHIVE VIEW state
│       │   ├── box_state.py        # BOX VIEW state
│       │   └── message_holder.py   # Message/Result manager
```


**代码风格及规范**

自解释，减少不必要的注释，仅在必要时使用英文注释；如无必要不使用缩写，使用全称（例如 current_project_id 而不是 cur_proj_id）

### 架构设计哲学

**一、整体架构哲学：单向分层，依赖递减**

```text
┌────────────────┐
│ Layout Manager │
│ Renderer       │← 渲染：只负责呈现
├────────────────┤
│ State Layer    │← 状态：协调与缓存
├────────────────┤
│ App            │← 应用：交互与 UI 入口
├────────────────┤
│ Actions        │← 业务：用户意图的直接表达
├────────────────┤
│ Models         │← 模型：数据的结构化
├────────────────┤
│ Database       │← 基础设施：持久化
└────────────────┘
```

核心原则：每一层只依赖下层，从不反向调用。

**二、数据层设计（Models）：约束即文档**

`models.py` - 领域的精确建模

设计精髓：
- 六实体模型直接映射各个载体：Track（轨道） → Project（项目） → Todo（行动） + Idea（萌芽） + Now（专注） + Takeaway（收获）
- CheckConstraint 作为活文档：archived 必有 archived_at_utc，代码即规则，不依赖应用层约束，数据库自己保证完整性。
- 双重身份设计：TodoItem.project_id 可为 NULL，优雅地统一了"结构化待办"与"收集箱待办"

`database.py` - 数据库核心逻辑及初始化

- 使用 `db_session` 上下文管理器 Context Manager，自动管理数据库连接的生命周期，为 actions.py 提供统一的数据库操作逻辑。

**三、业务层设计（Actions）：函数即意图`

`actions.py` - 业务意图的直接翻译

三大设计原则：
1. 用户语言命名：每个函数代表一个用户意图/行为
2. Result 模式统一返回：成功/失败、数据、消息三位一体，上层无需猜测。
3. ORM 边界清晰：Actions 内部使用 SQLAlchemy 对象，返回前解包为纯数据，上层永远不接触 ORM。

核心转变：从 v0.0.2 的调用 Service 层封装（纯 CRUD 包装）转变为直接操作数据库，避免重复代码，过度设计。（重构智慧：Service 层被移除是因为它不创造价值——它只是 Models 的简单转发。）

**四、状态层设计（States）：分而治之，各司其职**

`states/*` - 从单体到模块化的史诗级重构
  演进历程：
  - v0.0.2: state_deprecated.py - 单体巨石
  - v0.0.3: states/ (5个文件) - 视图级拆分

新架构的设计精髓：
1. AppState - 协调器模式：只管理全局切换，不持有业务数据
2. NowState - 专注计时 \
    NOW 行动器澄清：计时的时候不保存至数据库，而是保存在 TUI 状态中，对于 CLI，当前不设计计时功能。在停止后，用户确认之后（通常同时记录 Takeaways），才保存至数据库。
3. StructureState - 四层导航的复杂度驯服者
    ```python
    class StructureLevel(Enum):
        TRACKS                     # 1层：轨道列表
        TRACKS_WITH_PROJECTS_T     # 2层：轨道+项目（焦点在轨道）
        TRACKS_WITH_PROJECTS_P     # 3层：项目列表
        TODOS                      # 4层：待办列表
    ```
    - 状态缓存：_current_tracks_list, _current_projects_list 避免重复查询
    - 智能加载：load_current_lists() 根据 level 动态加载所需数据
    - 游标状态分离：每层独立维护 _current_track_idx, _current_project_idx
4. InfoState

**五、渲染层设计（Renderer）：纯渲染**

`renderer.py` - 纯渲染，不持有业务数据
```python
    # ✅ 只读 state 的缓存数据
    tracks = state.structure_state.current_tracks_list
    # ❌ 绝不调用 actions
    # tracks = actions.list_tracks_dict().data  # FORBIDDEN!
```
设计亮点：
1. 布局工具的抽象（一套工具统一所有 Box 视图的绘制）
2. 中文宽度精确处理
3. 分层渲染方法：**Content - Block 结构**，自顶向下的组合，每层只关心局部布局。

**六、应用层设计（App）：交互的指挥中心**

三大职责：
1. 键位绑定：按键含义随模式和视图动态变化
2. 布局组合：声明式的视图切换，不手动管理
3. 异步计时器循环

**架构演进**

重构时间线

| 版本    | 架构变化                   | 核心洞察                     |
|---------|----------------------------|------------------------------|
| v0.0.1  | TUI → Models → Database    | 初始原型                     |
| v0.0.2  | 引入 Service 层            | 误判：Service 只是 CRUD 包装 |
| v0.0.3a | 删除 Service，改为 Actions | 精简：用业务语义命名         |
| v0.0.3b | State 拆分为 states/       | 分治：单体到模块化           |
| v0.0.3c | Renderer 与 State 完全分离 | 纯化：数据缓存前移           |



delete 细节：
- Delete Track: 递归删除该 Track 下的所有 Projects、Todos、Sessions 和 Takeaways；解除 Ideas 与其 Projects 的关联（promoted_to_project_id → NULL）
- Delete Project: 递归删除该 Project 下的所有 Todos、Sessions 和 Takeaways；解除 Ideas 与该 Project 的关联（promoted_to_project_id → NULL）
- Delete Todo: 删除该 Todo 及其关联的所有 Sessions 和 Takeaways
- Delete Session: 删除该 Session，但保留关联的 Takeaways（now_session_id → NULL）
- Delete Takeaway: 直接删除该 Takeaway 




### 环境管理 (uv)

使用 uv 进行依赖管理，pyproject.toml 配置 `[project.scripts]` 使 `todo` 命令可用。

依赖：
typer, prompt-toolkit, sqlalchemy

### Code Hierarchy / Data Flow

```
cli.py
    -> tui/app.run()
        -> tui/state.AppState()
            -> tui/renderer.Renderer(tui_state)
        -> tui/app.key_bindings
            -> actions: excute action
                -> models: return model objects
```


### 数据库设计

SQLite 数据库，路径：`~/.mukitodo/todo.db`

数据库设计：

Track:
- id PRIMARY KEY
- name NOT NULL
- description
- status NOT NULL, DEFAULT 'active' (active / sleeping)
- archived: boolean, DEFAULT FALSE
- created_at_utc NOT NULL DEFAULT CURRENT_TIMESTAMP
- archived_at_utc
- order_index

Project:
- id PRIMARY KEY
- track_id NOT NULL, FOREIGN KEY REFERENCES Track(id)
- name NOT NULL
- description
- deadline_utc
- willingness_hint (0-3)
- importance_hint (0-3)
- urgency_hint (0-3)
- status NOT NULL, DEFAULT 'active' (active / focusing / sleeping / cancelled / finished)
- archived: boolean, DEFAULT FALSE
- created_at_utc NOT NULL DEFAULT CURRENT_TIMESTAMP
- started_at_utc
- finished_at_utc
- archived_at_utc
- order_index


TodoItem: (Structure Todo / Box Todo)
- id PRIMARY KEY
- project_id FOREIGN KEY REFERENCES Project(id) (nullable)
- name NOT NULL
- description
- url
- deadline_utc
- status NOT NULL, DEFAULT 'active' (active / done / sleeping / cancelled)
- archived: boolean, DEFAULT FALSE
- created_at_utc NOT NULL DEFAULT CURRENT_TIMESTAMP
- completed_at_utc
- archived_at_utc
- order_index

IdeaItem:
- id PRIMARY KEY
- name NOT NULL
- description
- maturity_hint (0-3)
- willingness_hint (0-3)
- status NOT NULL, DEFAULT 'active' (active / sleeping / deprecated / promoted)
- archived: boolean, DEFAULT FALSE
- created_at_utc NOT NULL DEFAULT CURRENT_TIMESTAMP
- archived_at_utc
- promoted_at_utc
- promoted_to_project_id FOREIGN KEY REFERENCES Project(id) (nullable) DEFAULT NULL
- order_index

NowSession: (Now Action Session)   (Attention: Only one of project_id or todo_item_id should be provided.)
- id PRIMARY KEY
- description
- project_id FOREIGN KEY REFERENCES Project(id) (nullable)
- todo_item_id FOREIGN KEY REFERENCES TodoItem(id) (nullable)
- duration_minutes NOT NULL
- started_at_utc NOT NULL
- ended_at_utc (NULL means saving on-going session)

Takeaway: (Attention: Only one of track_id, project_id, todo_item_id should be provided.)
- id PRIMARY KEY
- title NOT NULL
- content NOT NULL
- type NOT NULL (action / insight)
- date NOT NULL
- created_at_utc NOT NULL DEFAULT CURRENT_TIMESTAMP
- track_id FOREIGN KEY REFERENCES Track(id) (nullable)
- project_id FOREIGN KEY REFERENCES Project(id) (nullable)
- todo_item_id FOREIGN KEY REFERENCES TodoItem(id) (nullable)
- now_session_id FOREIGN KEY REFERENCES NowSession(id) (nullable)
