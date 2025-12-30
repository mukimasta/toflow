————————
MukiTodo — Version History / 更新记录
————————

### v0.01 2025-12-6 MVP

这是 MukiTodo 的第一个最小可用版本
我需要的不止是简单的分类 Todo 列表，而是以「项目」为核心的管理系统

版本主要内容：
1. 确定初始项目结构
2. 确定 Track -> Project -> Item 的 Todo 层级结构
3. 确定 TUI -> Actions -> Services -> Models -> Database 架构
4. 确定 TUI 界面，设计两种操作模式：NORMAL MODE 和 COMMAND MODE。NORMAL MODE 使用方向键这种符合直觉的操作方式，COMMAND MODE 则是命令模式，精确性、拓展性更强
5. 数据存储使用 SQLite 储存在 home 目录下
6. 实现 Track、Project、Item 的增删改查功能

### v0.0.2 2025-12-10 重大更新: 架构设计 / NOW 行动器

这是 MukiTodo 的第二个最小可用版本

1. 重新设计功能设计，逻辑完成 README 的初步编写，包括简介 / 理念，功能设计及设计理念，界面与交互设计等
2. 新增 NOW 行动器的实现
3. 重构 TUI 代码
    1. 重构 TUI state，使用 AppState 类管理状态，以及 NowState 类管理 NOW 行动器状态，StructureState 类管理结构状态
    2. 重构 TUI renderer，改为 OOP 逻辑，使用 Renderer 类管理渲染逻辑，优化显示
    3. 实现不同 View 下的不同 Layout 界面
```text
├── mukitodo/
│   ├── tui/                # prompt-toolkit TUI 应用
│   │   ├── __init__.py     # 初始化
│   │   ├── state.py        # 状态管理
│   │   ├── renderer.py     # 渲染器
│   │   └── app.py          # 按键绑定 + 启动入口
├── ...
```

v0.0.2 Code Hierarchy / Data Flow

```
cli.py
    -> tui/app.run()
        -> tui/state.AppState()
            -> tui/renderer.Renderer(tui_state)
        -> tui/app.key_bindings
            -> actions: excute action
                -> services: request database operations
                -> models: return model objects
```



### v0.0.3 (a) 重大更新: 全新功能设计 / 全新架构设计 / 全新数据库设计 / 大重构

大重构：
1. TUI 只负责交互，tui/app.py 在 tui/state.py 中读写 TUI 状态，所有操作仅与 actions.py 交互，TUI state 仅进行 UI 逻辑检查，不进行业务逻辑检查
2. 取消 Action -> Service -> Model 架构，改为 actions.py 直接操作数据库
3. 未来的 CLI 命令行入口将不再直接操作 AppState 状态，也通过 actions.py 行动

actions.py 设计原则：
1. 以业务操作命名，表达功能操作/用户意图
2. 不直接返回 Model 数据对象，而是通过 actions 解包为基础类型，例如 str / dict / list 数据
3. 未来同时支持 TUI 和 CLI
4. 使用 Context 管理数据库操作


数据库全面重新设计：
Track | Project | TodoItem | IdeaItem | NowSession | Takeaway

新功能架构设计：
1. Box 收集箱
2. ...

NOW 行动器澄清：计时的时候不保存至数据库，而是保存在 TUI 状态中，对于 CLI，当前不设计计时功能。在停止后，用户确认之后（通常同时记录 Takeaways），才保存至数据库。

待实现功能：
1. 当前版本 CLI 仅实现进入 TUI 和 help 两个命令
2. 排序功能

v0.0.3 Code Hierarchy / Data Flow

```
cli.py
    -> tui/app.run()
        -> tui/states/app_state.AppState()
            -> tui/renderer.Renderer(tui_state)
        -> tui/app.key_bindings
            -> actions: excute action
                -> models: return model objects
```

### v0.0.3 (b) 重大更新: TUI 重构

1. 重构 TUI 状态管理
    1. TUI 状态管理分为 View 和 UIModeState 两个部分
    2. 在 AppState 中综合管理 View 和 UIModeState 状态
    3. 不同的 View 使用不同的 State 类管理状态，目前有 NowState、StructureState、InfoState 三个状态类，分别管理自身 View 的状态
    4. 重构消息关系，使用 MessageHolder 类管理消息，所有 State 类都可以访问 MessageHolder 类
    5. 以优雅的原则重构了 AppState, NowState, StructureState, InfoState 类的实现
2. 重构 TUI 渲染器
    Renderer 实现原则：
    1. 只负责渲染，不负责业务逻辑
    2. 只与 State 类交互，不直接操作数据库，不与 actions.py 交互
3. 新增 View Info 视图，用于查看当前 Item 的详细信息

```
├── states/
│   ├── app_state.py
│   ├── info_state.py
│   ├── message_holder.py
│   ├── now_state.py
│   └── structure_state.py
```

### v0.0.3 (c) 2025-12-27 重大更新: 完善 TUI 架构，实现 Renderer 与 State 完全分离

1. 完善 State 类数据缓存，为 Renderer 提供可直接读取的数据，无需再调用 actions
2. 重构 app.py 布局设计
    1. 从 10 个 ConditionalContainer 优化为 4 个
    2. 每个 View 一个完整的 Container（NOW / STRUCTURE / INFO）为每个 View 提供独立的渲染方法
    3. Separator 和 Status Bar 改为全局共享，全宽显示
    4. 添加布局常量，集中管理参数
3. 完全移除 Renderer 对 actions 的依赖，所有数据从 State 读取（`now_state.current_project_dict` / `structure_state.current_tracks_list` 等）

架构优势：
- 数据流向单一：State → Renderer（Renderer 不再有副作用）
- 职责分离清晰：State 管理数据，Renderer 负责渲染
- 可维护性提升：布局结构一目了然，易于扩展

4. 完善 README.md 文档


### v0.0.4 (a) 状态切换以及排序功能、Archive 功能 2025-12-29

1. 实现 Item 的各状态切换功能（Sleep, Cancel, Archive, ...）✅
2. 实现 Structure View 根据 Item 状态排序功能并用不同样式显示✅
    - Track: Active > Sleeping
    - Project: Focusing > Active > Sleeping > Finished > Cancelled
    - Todo: Active > Sleeping > Done > Cancelled
3. 实现 Archive 面板（View）✅

### v0.0.4 (b) 实现 Timeline View



### v0.0.4 (c)


3. 完善 Item 的更多信息的样式显示
5. 实现 Takeaways 的记录功能 
6. 实现 Takeaways 面板（View）
7. 实现 NOW Done List 功能
8. 更改 Input Mode 显示及功能，Rename/Add Item 模式下，新增更多字段的编辑功能
    - Prompt 部分改为两行，第一行显示 Input Purpose Prompt，第二行显示类型切换按钮，例如 Takeaway.type (action/insight)
    - 输入框改为两行，第一行输入 Title/Name，第二行输入 Description/Content
    - Track Item 可编辑 Name, Description
    - Project Item 可编辑 Name, Description; Deadline, Willingness, Importance, Urgency, Started At
    - Todo Item 可编辑 Name, Description; URL, Deadline
    - Idea Item 可编辑 Name, Description; Maturity, Willingness, Status
    - Session Item 可编辑 Description; Started At, Duration, Ended At
    - Takeaway Item 可编辑 Title, Content, Type, Date


v0.0.5 计划：实现 Box 收集箱
