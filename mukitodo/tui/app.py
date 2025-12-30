import asyncio
from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl, BufferControl, ConditionalContainer, Dimension
from prompt_toolkit.styles import Style
from prompt_toolkit.filters import Condition

from .states.app_state import AppState, UIMode, View, InputPurpose, PendingAction
from .states.structure_state import StructureLevel, StructureState
from .states.now_state import TimerStateEnum, NowState
from .states.info_state import InfoState
from .renderer import Renderer


# ========================================
# Layout Constants
# ========================================

NOW_BOX_WIDTH = 60
NOW_PADDING_LEFT_RIGHT_WEIGHT = 6
NOW_PADDING_TOP_WEIGHT = 45
NOW_PADDING_BOTTOM_WEIGHT = 55


def run():
    state = AppState()
    renderer = Renderer(state)
    input_buffer = Buffer()

    # ========================================
    # Key Bindings
    # ========================================
    kb = KeyBindings()

    is_normal_mode = Condition(lambda: state.ui_mode_state.mode == UIMode.NORMAL)
    is_command_mode = Condition(lambda: state.ui_mode_state.mode == UIMode.COMMAND)
    is_input_mode = Condition(lambda: state.ui_mode_state.mode == UIMode.INPUT)
    is_confirm_mode = Condition(lambda: state.ui_mode_state.mode == UIMode.CONFIRM)

    is_now_view = Condition(lambda: state.view == View.NOW)
    is_structure_view = Condition(lambda: state.view == View.STRUCTURE)
    is_info_view = Condition(lambda: state.view == View.INFO)
    is_archive_view = Condition(lambda: state.view == View.ARCHIVE)


    # == General Key Bindings ==

    @kb.add("c-c")
    @kb.add("c-d")
    def _(event):
        event.app.exit()

    # == Normal Mode Key Bindings ==

    @kb.add("q", filter=is_normal_mode)
    def _(event):
        state.ask_confirm(PendingAction.QUIT)
    @kb.add("q", filter=is_confirm_mode)
    def _(event):
        confirm_action = state.ui_mode_state.confirm_action
        assert confirm_action is not None
        if confirm_action == PendingAction.QUIT:
            event.app.exit()
        state.cancel_confirm()

    @kb.add("tab", filter=is_normal_mode)
    def _(event):
        state.switch_view()

    @kb.add("A", filter=is_normal_mode)
    def _(event):
        """Enter Archive View from any view."""
        state.enter_archive_view()


    # @kb.add(":", filter=is_normal_mode)
    # @kb.add(">", filter=is_normal_mode)
    # def _(event):
    #     state.change_mode(UIMode.COMMAND)


    # TODO: Toggle Box: Shift


    # Normal Mode & Structure View

    @kb.add("up", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.structure_state.move_cursor(-1)
    @kb.add("down", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.structure_state.move_cursor(1)
    @kb.add("right", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.structure_state.select_current()
    @kb.add("left", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.structure_state.go_back()

    @kb.add("i", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.open_item_info()

    @kb.add("=", filter=is_normal_mode & is_structure_view)
    @kb.add("+", filter=is_normal_mode & is_structure_view)
    def _(event):
        input_buffer.reset()
        default_value = state.start_input_and_return_default_value(InputPurpose.STRUCTURE_ADD_ITEM)
        if default_value is not None:
            input_buffer.reset()
            input_buffer.text = default_value
            input_buffer.cursor_position = len(default_value)

    @kb.add("r", filter=is_normal_mode & is_structure_view)
    def _(event):
        default_value = state.start_input_and_return_default_value(InputPurpose.STRUCTURE_RENAME_ITEM)
        if default_value is not None:
            input_buffer.reset()
            input_buffer.text = default_value
            input_buffer.cursor_position = len(default_value)
    
    @kb.add("backspace", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.ask_confirm(PendingAction.DELETE_STRUCTURE_ITEM)
    @kb.add("backspace", filter=is_confirm_mode & is_structure_view)
    def _(event):
        confirm_action = state.ui_mode_state.confirm_action
        assert confirm_action is not None
        if confirm_action == PendingAction.DELETE_STRUCTURE_ITEM:
            state.structure_state.delete_selected_item()
        state.cancel_confirm()

    @kb.add("space", filter=is_normal_mode & is_structure_view)
    def _(event):
        """
        Toggle item status:
        - TODOS level: Todo done ↔ active (or other → active)
        - TRACKS_WITH_PROJECTS_P level: Project finished ↔ active (or other → active)
        """
        state.structure_state.toggle_selected_item()

    @kb.add("s", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.structure_state.sleep_selected_item()

    @kb.add("c", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.structure_state.cancel_selected_item()

    @kb.add("f", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.structure_state.focus_selected_item()

    @kb.add("a", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.ask_confirm(PendingAction.ARCHIVE_STRUCTURE_ITEM)
    @kb.add("a", filter=is_confirm_mode & is_structure_view)
    def _(event):
        confirm_action = state.ui_mode_state.confirm_action
        assert confirm_action is not None
        if confirm_action == PendingAction.ARCHIVE_STRUCTURE_ITEM:
            state.structure_state.archive_selected_item()
        state.cancel_confirm()

    @kb.add("enter", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.ask_confirm(PendingAction.ENTER_NOW_WITH_STRUCTURE_ITEM)
    @kb.add("enter", filter=is_confirm_mode & is_structure_view)
    def _(event):
        confirm_action = state.ui_mode_state.confirm_action
        assert confirm_action is not None
        if confirm_action == PendingAction.ENTER_NOW_WITH_STRUCTURE_ITEM:
            state.enter_now_with_structure_item()
        state.cancel_confirm()

    # Normal Mode & NOW View

    @kb.add("space", filter=is_normal_mode & is_now_view)
    def _(event):
        state.now_state.toggle_timer()

    @kb.add("r", filter=is_normal_mode & is_now_view)
    def _(event):
        state.now_state.reset_timer()
    
    @kb.add("+", filter=is_normal_mode & is_now_view)
    @kb.add("=", filter=is_normal_mode & is_now_view)
    def _(event):
        state.now_state.adjust_time(5)
    @kb.add("-", filter=is_normal_mode & is_now_view)
    def _(event):
        state.now_state.adjust_time(-5)

    @kb.add("i", filter=is_normal_mode & is_now_view)
    def _(event):
        state.open_item_info()


    @kb.add("enter", filter=is_normal_mode & is_now_view)
    def _(event):
        state.ask_confirm(PendingAction.FINISH_SESSION)
    
    @kb.add("enter", filter=is_confirm_mode & is_now_view)
    def _(event):
        confirm_action = state.ui_mode_state.confirm_action
        assert confirm_action is not None
        if confirm_action == PendingAction.FINISH_SESSION:
            state.finish_session()
        state.cancel_confirm()

    # INFO view specific key bindings
    
    @kb.add("i", filter=is_normal_mode & is_info_view)
    @kb.add("escape", filter=is_normal_mode & is_info_view)
    def _(event):
        state.return_from_info()
    
    @kb.add("up", filter=is_normal_mode & is_info_view)
    def _(event):
        state.info_state.move_cursor(-1)
    
    @kb.add("down", filter=is_normal_mode & is_info_view)
    def _(event):
        state.info_state.move_cursor(1)
    
    @kb.add("r", filter=is_normal_mode & is_info_view)
    def _(event):
        default_value = state.start_input_and_return_default_value(InputPurpose.INFO_EDIT_FIELD)
        if default_value is not None:
            input_buffer.reset()
            input_buffer.text = default_value
            input_buffer.cursor_position = len(default_value)

    # ARCHIVE view specific key bindings

    @kb.add("up", filter=is_normal_mode & is_archive_view)
    def _(event):
        state.archive_state.move_cursor(-1)

    @kb.add("down", filter=is_normal_mode & is_archive_view)
    def _(event):
        state.archive_state.move_cursor(1)

    @kb.add("u", filter=is_normal_mode & is_archive_view)
    def _(event):
        """Unarchive selected item."""
        state.ask_confirm(PendingAction.UNARCHIVE_ITEM)

    @kb.add("u", filter=is_confirm_mode & is_archive_view)
    def _(event):
        confirm_action = state.ui_mode_state.confirm_action
        assert confirm_action is not None
        if confirm_action == PendingAction.UNARCHIVE_ITEM:
            state.archive_state.unarchive_selected_item()
        state.cancel_confirm()

    @kb.add("backspace", filter=is_normal_mode & is_archive_view)
    def _(event):
        """Delete selected item permanently."""
        state.ask_confirm(PendingAction.DELETE_ARCHIVE_ITEM)

    @kb.add("backspace", filter=is_confirm_mode & is_archive_view)
    def _(event):
        confirm_action = state.ui_mode_state.confirm_action
        assert confirm_action is not None
        if confirm_action == PendingAction.DELETE_ARCHIVE_ITEM:
            state.archive_state.delete_selected_item()
        state.cancel_confirm()

    @kb.add("i", filter=is_normal_mode & is_archive_view)
    def _(event):
        """View info of selected archived item."""
        state.open_item_info()

    @kb.add("escape", filter=is_normal_mode & is_archive_view)
    @kb.add("A", filter=is_normal_mode & is_archive_view)
    def _(event):
        """Exit Archive View (return to STRUCTURE)."""
        state.exit_archive_view()


    # == Input Mode Key Bindings ==

    @kb.add("escape", filter=is_input_mode)
    @kb.add("c-g", filter=is_input_mode)
    def _(event):
        state.cancel_input()
        input_buffer.reset()

    @kb.add("enter", filter=is_input_mode)
    def _(event):
        input_value = input_buffer.text.strip()
        state.confirm_input(input_value)
        input_buffer.reset()


    # == Confirm Mode Key Bindings ==
    
    @kb.add("<any>", filter=is_confirm_mode)
    def _(event):
        state.cancel_confirm()

    # == Command Mode Key Bindings ==

    # TODO: Command Mode Key Bindings


    # ========================================
    # Layout
    # ========================================

    layout = Layout(
        HSplit([
            # ============================================
            # NOW View (centered main content with padding)
            # ============================================
            ConditionalContainer(
                HSplit([
                    # Top padding
                    Window(height=Dimension(weight=NOW_PADDING_TOP_WEIGHT)),

                    # Main content (centered)
                    VSplit([
                        Window(width=Dimension(weight=NOW_PADDING_LEFT_RIGHT_WEIGHT)),
                        Window(
                            content=FormattedTextControl(renderer.render_now_view_content),
                            width=Dimension(preferred=NOW_BOX_WIDTH),
                            wrap_lines=False
                        ),
                        Window(width=Dimension(weight=NOW_PADDING_LEFT_RIGHT_WEIGHT)),
                    ]),

                    # Bottom padding
                    Window(height=Dimension(weight=NOW_PADDING_BOTTOM_WEIGHT)),
                ]),
                filter=is_now_view
            ),

            # ============================================
            # STRUCTURE View (full-width main content)
            # ============================================
            ConditionalContainer(
                Window(
                    content=FormattedTextControl(renderer.render_structure_view_content),
                    wrap_lines=True
                ),
                filter=is_structure_view
            ),

            # ============================================
            # INFO View (full-width main content)
            # ============================================
            ConditionalContainer(
                Window(
                    content=FormattedTextControl(renderer.render_info_view_content),
                    wrap_lines=True
                ),
                filter=is_info_view
            ),

            # ============================================
            # ARCHIVE View (full-width main content)
            # ============================================
            ConditionalContainer(
                Window(
                    content=FormattedTextControl(renderer.render_archive_view_content),
                    wrap_lines=True
                ),
                filter=is_archive_view
            ),

            # ============================================
            # Separator (shared, full-width)
            # ============================================
            Window(height=1, char="─", style="class:separator"),

            # ============================================
            # Status Bar (shared, full-width)
            # ============================================
            Window(
                content=FormattedTextControl(renderer.render_status_line),
                height=1
            ),

            # ============================================
            # Input/Command Mode Area (shared)
            # ============================================
            ConditionalContainer(
                HSplit([
                    VSplit([
                        Window(content=FormattedTextControl(renderer.render_mode_indicator), width=10),
                        Window(content=FormattedTextControl(renderer.render_prompt), width=2),
                        Window(content=BufferControl(buffer=input_buffer)),
                    ], height=1),
                ]),
                filter=is_command_mode | is_input_mode,
            ),
        ])
    )

    style = Style.from_dict({
        "dim": "ansibrightblack",
        "track": "bold",
        "selected": "reverse",
        "selected_track": "bold ansicyan",
        "unselected_track": "ansibrightblack",
        "header": "bold ansiblue",
        "done": "ansibrightblack",
        "success": "ansigreen",
        "error": "ansired",
        "warning": "ansiyellow",
        "separator": "ansibrightblack",
        "mode": "bg:ansiblue ansiwhite",
        "prompt": "bold",
        "timer_idle": "bold",
        "timer_running": "bold ansigreen",
        "timer_paused": "bold ansiyellow",

        # Track status styles
        "track.active": "",
        "track.sleeping": "ansibrightblack",

        # Project status styles
        "project.focusing": "bold",
        "project.active": "",
        "project.sleeping": "ansibrightblack",
        "project.finished": "ansibrightblack",
        "project.cancelled": "ansibrightblack strike",

        # Todo status styles
        "todo.active": "",
        "todo.sleeping": "ansibrightblack",
        "todo.done": "ansibrightblack",
        "todo.cancelled": "ansibrightblack strike",

        # Archive view styles
        "idea.archived": "ansibrightblack",
        "todo.archived": "ansibrightblack",
    })

    app = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=True,
    )

    # Async timer update loop
    async def update_timer_loop():
        """Background task to update timer frequently, refresh only when needed."""
        while True:
            await asyncio.sleep(0.1)  # Check 10 times per second for responsiveness
            if state.view == View.NOW and state.now_state.timer_state == TimerStateEnum.RUNNING:
                # Only invalidate if timer seconds actually changed
                if state.now_state.update_timer():
                    app.invalidate()
    
    # Run app with async timer
    async def run_async():
        asyncio.create_task(update_timer_loop())
        await app.run_async()
    
    asyncio.run(run_async())
