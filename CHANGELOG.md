————————
MukiTodo — Version History / 更新记录
————————

### v0.01: MVP | 2025-12-6

这是 MukiTodo 的第一个最小可用版本
我需要的不止是简单的分类 Todo 列表，而是以「项目」为核心的管理系统

版本主要内容：
1. 确定初始项目结构
2. 确定 Track -> Project -> Item 的 Todo 层级结构
3. 确定 TUI 界面，设计两种操作模式：NORMAL MODE 和 COMMAND MODE。NORMAL MODE 使用方向键这种符合直觉的操作方式，COMMAND MODE 则是命令模式，精确性、拓展性更强
4. 数据存储使用 SQLite 储存在 home 目录下
5. 实现 Track、Project、Item 的增删改查功能

### v0.0.2 重大更新: 架构设计 / NOW 行动器 | 2025-12-10

这是 MukiTodo 的第二个最小可用版本

1. 重新设计功能设计，逻辑完成 README 的初步编写，包括简介 / 理念，功能设计及设计理念，界面与交互设计等
2. 重构 TUI 代码
    1. 重构 TUI state，使用 AppState 类管理状态，以及 NowState 类管理 NOW 行动器状态，StructureState 类管理结构状态
    2. 重构 TUI renderer，改为 OOP 逻辑，使用 Renderer 类管理渲染逻辑，优化显示
    3. 实现不同 View 下的不同 Layout 界面
3. 新增 NOW 行动器的实现

