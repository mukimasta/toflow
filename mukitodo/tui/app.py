import asyncio
from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl, BufferControl, ConditionalContainer, Dimension
from prompt_toolkit.styles import Style
from prompt_toolkit.filters import Condition

from .state import AppState, StructureLevel, UIMode, View, TimerState, InputPurpose
from .renderer import Renderer


def run():
    state = AppState()
    input_buffer = Buffer()
    renderer = Renderer(state)

    def get_main_content():
        return renderer.render_main_content()

    def get_status_line():
        return renderer.render_status_line()

    def get_mode_indicator():
        return renderer.render_mode_indicator()

    def get_prompt():
        return renderer.render_prompt()

    kb = KeyBindings()

    is_normal = Condition(lambda: state.mode == UIMode.NORMAL)
    is_command = Condition(lambda: state.mode == UIMode.COMMAND)
    is_input = Condition(lambda: state.mode == UIMode.INPUT)
    is_confirm = Condition(lambda: state.mode == UIMode.CONFIRM)
    is_now = Condition(lambda: state.view == View.NOW)
    is_structure = Condition(lambda: state.view == View.STRUCTURE)



    @kb.add("c-c")
    @kb.add("c-d")
    def _(event):
        event.app.exit()

    # Normal Mode Key Bindings

    @kb.add("q", filter=is_normal)
    def _(event):
        state.ask_confirm("quit", "q")

    @kb.add("up", filter=is_normal)
    def _(event):
        state.move_cursor(-1)

    @kb.add("down", filter=is_normal)
    def _(event):
        state.move_cursor(1)

    @kb.add("right", filter=is_normal)
    def _(event):
        state.select_current()

    @kb.add("left", filter=is_normal)
    def _(event):
        state.go_back()

    @kb.add("tab", filter=is_normal)
    def _(event):
        if state.view == View.NOW:
            state.change_view(View.STRUCTURE)
        else:
            state.change_view(View.NOW)


    # STRUCTURE view specific key bindings
    
    @kb.add("t", filter=is_normal & is_structure)
    def _(event):
        state.toggle_display_mode()

    @kb.add("space", filter=is_normal & is_structure)
    def _(event):
        if state.structure_state.current_todos_list != []:
            state.ask_confirm("toggle_todo_structure", "space")

    @kb.add("backspace", filter=is_normal & is_structure)
    def _(event):
        state.ask_confirm("delete", "backspace")

    @kb.add("=", filter=is_normal & is_structure)
    @kb.add("+", filter=is_normal & is_structure)
    def _(event):
        state.change_mode(UIMode.INPUT, InputPurpose.ADD)

    @kb.add("r", filter=is_normal & is_structure)
    def _(event):
        current_name = state.start_rename()
        if current_name:
            input_buffer.text = current_name
            input_buffer.cursor_position = len(current_name)
    
    @kb.add("enter", filter=is_normal & is_structure)
    def _(event):
        # Try to enter NOW view from current structure position
        state.try_enter_now_from_structure()
    
    # NOW view specific key bindings
    
    @kb.add("space", filter=is_normal & is_now)
    def _(event):
        state.toggle_timer()
        event.app.invalidate()  # Immediate visual feedback
    
    @kb.add("r", filter=is_normal & is_now)
    def _(event):
        state.reset_timer()
        event.app.invalidate()  # Immediate visual feedback
    
    @kb.add("+", filter=is_normal & is_now)
    @kb.add("=", filter=is_normal & is_now)
    def _(event):
        state.adjust_timer(5)
        event.app.invalidate()  # Immediate visual feedback
    
    @kb.add("-", filter=is_normal & is_now)
    def _(event):
        state.adjust_timer(-5)
        event.app.invalidate()  # Immediate visual feedback
    
    @kb.add("enter", filter=is_normal & is_now)
    def _(event):
        state.ask_confirm("toggle_todo_now", "enter")
        event.app.invalidate()  # Immediate visual feedback

    @kb.add(":", filter=is_normal)
    @kb.add(">", filter=is_normal)
    def _(event):
        state.change_mode(UIMode.COMMAND)



    # Command Mode Key Bindings

    @kb.add("escape", filter=is_command)
    @kb.add("c-g", filter=is_command)
    def _(event):
        state.change_mode(UIMode.NORMAL)
        input_buffer.reset()

    @kb.add("q", filter=is_command)
    def _(event):
        if not input_buffer.text:
            state.change_mode(UIMode.NORMAL)
        else:
            input_buffer.insert_text("q")

    @kb.add("enter", filter=is_command)
    def _(event):
        cmd = input_buffer.text.strip()
        input_buffer.reset()

        if not cmd:
            state.change_mode(UIMode.NORMAL)
            return

        if cmd.lower() in ("q", "quit"):
            event.app.exit()
            return

        state.execute_command(cmd)
        state.change_mode(UIMode.NORMAL)


    # Input Mode Key Bindings

    @kb.add("escape", filter=is_input)
    @kb.add("c-g", filter=is_input)
    def _(event):
        state.change_mode(UIMode.NORMAL)
        input_buffer.reset()

    @kb.add("enter", filter=is_input)
    def _(event):
        name = input_buffer.text.strip()
        input_buffer.reset()

        if name:
            if state.input_purpose == InputPurpose.ADD:
                state.add_new_item(name)
            elif state.input_purpose == InputPurpose.RENAME:
                state.rename_current_item(name)
        
        state.change_mode(UIMode.NORMAL)


    # Confirm Mode Key Bindings

    @kb.add("q", filter=is_confirm)
    def _(event):
        if state.pending_key == "q":
            event.app.exit()
        else:
            state.cancel_confirm()

    @kb.add("backspace", filter=is_confirm)
    def _(event):
        if state.pending_key == "backspace":
            state.cancel_confirm()
            state.delete_current()
        else:
            state.cancel_confirm()

    @kb.add("space", filter=is_confirm)
    def _(event):
        if state.pending_key == "space":
            state.cancel_confirm()
            state.toggle_current_todo()
        else:
            state.cancel_confirm()

    @kb.add("enter", filter=is_confirm)
    def _(event):
        if state.pending_key == "enter":
            state.cancel_confirm()
            state.mark_now_todo_done()
            event.app.invalidate()  # Immediate visual feedback
        else:
            state.cancel_confirm()

    # Any other key cancels confirmation
    @kb.add("<any>", filter=is_confirm)
    def _(event):
        state.cancel_confirm()


    layout = Layout(
        HSplit([
            # ========================================
            # NOW View: Centered box layout
            # ========================================
            ConditionalContainer(
                HSplit([
                    # Top padding (45%)
                    Window(height=Dimension(weight=45)),
                    
                    # Centered content area
                    VSplit([
                        # Left padding
                        Window(width=Dimension(weight=6)),
                        
                        # NOW content box (max width 60)
                        Window(
                            content=FormattedTextControl(get_main_content),
                            width=Dimension(preferred=60),
                            wrap_lines=False
                        ),
                        
                        # Right padding
                        Window(width=Dimension(weight=6)),
                    ]),
                    
                    # Bottom padding (55%)
                    Window(height=Dimension(weight=55)),
                ]),
                filter=is_now
            ),
            
            # ========================================
            # STRUCTURE View: Full screen layout
            # ========================================
            ConditionalContainer(
                Window(
                    content=FormattedTextControl(get_main_content),
                    wrap_lines=True
                ),
                filter=is_structure
            ),
            
            # ========================================
            # Shared bottom elements (all views)
            # ========================================
            
            # Separator - centered in NOW view
            ConditionalContainer(
                VSplit([
                    Window(width=Dimension(weight=1)),
                    Window(height=1, char="─", width=Dimension(preferred=60)),
                    Window(width=Dimension(weight=1)),
                ]),
                filter=is_now
            ),
            
            # Separator - full width in STRUCTURE view
            ConditionalContainer(
                Window(height=1, char="─", style="class:separator"),
                filter=is_structure
            ),
            
            # Status bar - centered in NOW view
            ConditionalContainer(
                VSplit([
                    Window(width=Dimension(weight=1)),
                    Window(
                        content=FormattedTextControl(get_status_line),
                        height=1,
                        width=Dimension(preferred=60)
                    ),
                    Window(width=Dimension(weight=1)),
                ]),
                filter=is_now
            ),
            
            # Status bar - full width in STRUCTURE view
            ConditionalContainer(
                Window(content=FormattedTextControl(get_status_line), height=1),
                filter=is_structure
            ),
            
            # Input/command mode container (unchanged)
            ConditionalContainer(
                HSplit([
                    VSplit([
                        Window(content=FormattedTextControl(get_mode_indicator), width=10),
                        Window(content=FormattedTextControl(get_prompt), width=2),
                        Window(content=BufferControl(buffer=input_buffer)),
                    ], height=1),
                ]),
                filter=is_command | is_input,
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
            if state.view == View.NOW and state.now_state.timer_state == TimerState.RUNNING:
                # Only invalidate if timer seconds actually changed
                if state.now_state.update_timer():
                    app.invalidate()
    
    # Run app with async timer
    async def run_async():
        asyncio.create_task(update_timer_loop())
        await app.run_async()
    
    asyncio.run(run_async())
