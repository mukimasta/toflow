"""TUI Application — entry point, key bindings, prompt-toolkit wiring."""

import asyncio

from prompt_toolkit import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    ConditionalContainer,
    HSplit,
    Layout,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl

from toflow.tui.display import (
    APP_STYLE,
    apply_zen_layout,
    clip_to_viewport,
    flatten,
    render_input_form_lines,
    render_status,
    render_title,
    truncate_lines,
)
from toflow.ops.result import Result
from toflow.tui.input.intent import InputIntent
from toflow.tui.input.service import FormService
from toflow.tui.now.runtime import run_timer_runtime
from toflow.tui.state import AppState, UIMode
from toflow.tui.view.archive import ArchiveView
from toflow.tui.view.box import BoxProjectsView, BoxTodosView
from toflow.tui.view.picker import PickerView
from toflow.tui.view.timeline import TimelineView


def run() -> None:
    state = AppState()
    form_service = FormService()

    # -- Conditions --

    is_normal = Condition(lambda: state.ui_mode == UIMode.NORMAL)
    is_confirm = Condition(lambda: state.ui_mode == UIMode.CONFIRM)
    is_input = Condition(lambda: state.ui_mode == UIMode.INPUT and state.has_form)
    is_now_active = Condition(state.is_now_active)
    def _is_zen_layout() -> bool:
        return getattr(state.current_view.pane, "layout_mode", "default") == "zen"

    is_zen_layout = Condition(_is_zen_layout)

    def _now_note_input() -> bool:
        if not state.is_now_active():
            return False
        return state.now.is_note_input()

    is_now_note_input = Condition(_now_note_input)

    # -- Content --

    def get_title_content() -> list[tuple[str, str]]:
        return render_title(state)

    def get_main_content() -> list[tuple[str, str]]:
        try:
            from prompt_toolkit.application.current import get_app
            app = get_app()
            rows = app.output.get_size().rows
            cols = app.output.get_size().columns
        except Exception:
            rows, cols = 24, 80

        reserved = 2 if _is_zen_layout() else 3  # separator + status (+ title if not zen)
        if state.ui_mode == UIMode.INPUT and state.has_form and state.input_session is not None:
            session = state.input_session
            form_lines = render_input_form_lines(
                session.form,
                mode_label=session.mode_label,
                entity_label=session.entity_type.value.title(),
                width=cols,
            )
            reserved += max(1, len(form_lines))
        vh = max(1, rows - reserved)

        pane = state.current_view.pane
        lines = pane.render()
        if getattr(pane, "layout_mode", "default") == "zen":
            if state.current_view.title:
                lines = [[("", state.current_view.title)], [("", "")], *lines]
            lines = truncate_lines(lines, cols)
            lines = apply_zen_layout(lines, cols, vh)
            return flatten(lines)

        lines = truncate_lines(lines, cols)
        sel_line = pane.selected_line_index()
        block_range = getattr(pane, "selected_block_range", lambda: None)()
        lines, pane.viewport_start = clip_to_viewport(
            lines, vh, sel_line, pane.viewport_start, block_range=block_range
        )
        return flatten(lines)

    def get_status_content() -> list[tuple[str, str]]:
        if state.ui_mode == UIMode.INPUT:
            return [("class:dim", "  [Tab] next  [←/→] move  [Ctrl/⌥←→] word  [Shift] select  [Ctrl+V] paste  [=/-] adjust  [Enter] ok  [Esc] cancel")]
        return render_status(
            is_confirm=state.ui_mode == UIMode.CONFIRM,
            last_result=state.last_result,
            status_hint=state.current_view.status_hint,
        )

    def _terminal_cols() -> int:
        try:
            from prompt_toolkit.application.current import get_app
            return get_app().output.get_size().columns
        except Exception:
            return 80

    def get_form_content() -> list[tuple[str, str]]:
        session = state.input_session
        if session is None:
            return []
        lines = render_input_form_lines(
            session.form,
            mode_label=session.mode_label,
            entity_label=session.entity_type.value.title(),
            width=_terminal_cols(),
        )
        return flatten(lines)

    # -- Key bindings --

    kb = KeyBindings()

    def _safe_add(*primary_keys: str, fallback_keys: tuple[str, ...] | None = None, filter=None):
        """Try primary keys (e.g. m-up); fallback to escape-prefixed if unsupported."""
        try:
            return kb.add(*primary_keys, filter=filter)
        except ValueError:
            if not fallback_keys:
                raise
            return kb.add(*fallback_keys, filter=filter)

    @kb.add("c-c")
    @kb.add("c-d")
    def _force_quit(event):
        event.app.exit()

    # == Normal mode ==

    @kb.add("<any>", filter=is_normal & is_now_note_input, eager=True)
    def _now_note_key_router(event):
        if not event.key_sequence:
            return
        key = event.key_sequence[0].key
        result = state.now.handle_note_key(key, event.data)
        if result is not None:
            state.last_result = result

    @kb.add("q", filter=is_normal)
    def _quit(event):
        state.request_confirm(lambda: (event.app.exit(), None)[-1], "q")

    @kb.add("[", filter=is_normal)
    def _open_box_todos(event):
        state.toggle_secondary(BoxTodosView)

    @kb.add("]", filter=is_normal)
    def _open_box_projects(event):
        state.toggle_secondary(BoxProjectsView)

    @kb.add("tab", filter=is_normal)
    def _switch_primary(event):
        state.switch_primary()

    @kb.add("`", filter=is_normal)
    def _open_archive(event):
        state.toggle_secondary(ArchiveView)

    @kb.add("'", filter=is_normal)
    def _open_timeline(event):
        state.toggle_secondary(TimelineView)

    @kb.add("up", filter=is_normal)
    def _up(event):
        state.current_view.move(-1)

    @kb.add("down", filter=is_normal)
    def _down(event):
        state.current_view.move(1)

    @kb.add("right", filter=is_normal)
    def _right(event):
        state.current_view.go_deeper(state)

    @kb.add("left", filter=is_normal)
    def _left(event):
        state.go_back()

    @kb.add("space", filter=is_normal)
    def _toggle(event):
        result = state.current_view.space_action()
        if result is not None:
            state.last_result = result

    @kb.add("backspace", filter=is_normal)
    def _delete(event):
        if state.is_now_active() and state.now.consume_note_backspace():
            return
        state.request_confirm(state.current_view.delete_selected, "backspace")

    @kb.add("=", filter=is_normal & ~is_now_active)
    @kb.add("+", filter=is_normal & ~is_now_active)
    def _add(event):
        if not state.current_view.can_add:
            return
        session = form_service.build_add_session(
            state.current_view.add_entity_type(),
            state.current_view.add_parent_id(),
            state.current_view.add_insert_after_id(),
        )
        if session is not None:
            state.start_input(session)

    @kb.add("r", filter=is_normal & ~is_now_active)
    def _edit(event):
        if not state.current_view.can_edit:
            return
        selected_id = state.current_view.selected_id()
        if selected_id is None:
            return
        session = form_service.build_edit_session(
            state.current_view.entity_type,
            selected_id,
        )
        if session is not None:
            state.start_input(session)

    @kb.add("m", filter=is_normal)
    def _move(event):
        ctx = state.current_view.move_context()
        if ctx is not None:
            state.open_modal(PickerView(ctx))

    @kb.add("enter", filter=is_normal)
    def _confirm(event):
        state.current_view.confirm_selection(state)

    @kb.add("a", filter=is_normal)
    def _archive(event):
        action = state.current_view.archive_confirm_action()
        if action is not None:
            state.request_confirm(action, "a")

    @kb.add("s", filter=is_normal)
    @kb.add("z", filter=is_normal)
    def _sleep(event):
        result = state.current_view.sleep_selected()
        if result is not None:
            state.last_result = result

    @kb.add("c", filter=is_normal)
    def _cancel(event):
        result = state.current_view.cancel_selected()
        if result is not None:
            state.last_result = result

    @kb.add("p", filter=is_normal)
    def _pin(event):
        result = state.current_view.pin_selected()
        if result is not None:
            state.last_result = result

    @_safe_add("m-up", fallback_keys=("escape", "up"), filter=is_normal)
    def _reorder_up(event):
        result = state.current_view.reorder_selected(-1)
        if result is not None:
            state.last_result = result

    @_safe_add("m-down", fallback_keys=("escape", "down"), filter=is_normal)
    def _reorder_down(event):
        result = state.current_view.reorder_selected(1)
        if result is not None:
            state.last_result = result

    @kb.add("t", filter=is_normal & is_now_active)
    def _toggle_today_panel(event):
        state.now.toggle_today_panel()

    @kb.add("=", filter=is_normal & is_now_active)
    @kb.add("+", filter=is_normal & is_now_active)
    def _now_plus(event):
        result = state.now.adjust_current(1)
        if result is not None:
            state.last_result = result

    @kb.add("-", filter=is_normal & is_now_active)
    def _now_minus(event):
        result = state.now.adjust_current(-1)
        if result is not None:
            state.last_result = result

    @kb.add("r", filter=is_normal & is_now_active)
    def _now_r(event):
        req = state.now.reset_confirm_request()
        if req is not None:
            state.request_confirm(req.action, req.trigger_key)

    @kb.add("n", filter=is_normal & is_now_active)
    def _now_note(event):
        result = state.now.open_note()
        if result is not None:
            state.last_result = result

    @kb.add("escape", filter=is_normal)
    def _escape(event):
        if state.is_now_active():
            result = state.now.close_note_if_open()
            if result is not None:
                state.last_result = result
                return
        state.go_back()

    # == Confirm mode ==

    @kb.add("enter", filter=is_confirm)
    @kb.add("backspace", filter=is_confirm)
    @kb.add("q", filter=is_confirm)
    @kb.add("<any>", filter=is_confirm)
    def _confirm_key(event):
        if not event.key_sequence:
            state.handle_confirm_key("")
            return
        pressed = event.key_sequence[0].key
        state.handle_confirm_key(pressed)

    # == Input mode — form (multi-field, inline editing) ==

    @kb.add("enter", filter=is_input)
    def _form_submit(event):
        session = state.take_input_session()
        if session is None:
            return
        result = form_service.submit(session)
        state.last_result = result
        if result.success:
            state.current_view.load_data()

    @kb.add("escape", filter=is_input)
    @kb.add("c-g", filter=is_input)
    def _form_cancel(event):
        state.cancel_input()

    @kb.add("tab", filter=is_input)
    @kb.add("down", filter=is_input)
    def _form_next(event):
        form = state.form
        if form is not None:
            form.handle_intent(InputIntent.FIELD_NEXT)

    @kb.add("s-tab", filter=is_input)
    @kb.add("up", filter=is_input)
    def _form_prev(event):
        form = state.form
        if form is not None:
            form.handle_intent(InputIntent.FIELD_PREV)

    def _read_clipboard_text(event) -> str:
        """Best-effort clipboard read for Ctrl+V (prompt_toolkit, then macOS pbpaste)."""
        try:
            data = event.app.clipboard.get_data()
            text = getattr(data, "text", None)
            if text:
                return text
        except Exception:
            pass
        try:
            import subprocess

            result = subprocess.run(
                ["pbpaste"],
                check=False,
                capture_output=True,
                text=True,
                timeout=0.5,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except Exception:
            pass
        return ""

    @kb.add("left", filter=is_input)
    def _form_cursor_left(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.SEG_PREV)

    @kb.add("right", filter=is_input)
    def _form_cursor_right(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.SEG_NEXT)

    @kb.add("s-left", filter=is_input)
    def _form_select_left(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.SEG_PREV, shift=True)

    @kb.add("s-right", filter=is_input)
    def _form_select_right(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.SEG_NEXT, shift=True)

    @kb.add("c-left", filter=is_input)
    @kb.add("escape", "left", filter=is_input)
    @kb.add("escape", "b", filter=is_input)
    def _form_word_left(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.WORD_PREV)

    @kb.add("c-right", filter=is_input)
    @kb.add("escape", "right", filter=is_input)
    @kb.add("escape", "f", filter=is_input)
    def _form_word_right(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.WORD_NEXT)

    @kb.add("c-s-left", filter=is_input)
    def _form_select_word_left(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.WORD_PREV, shift=True)

    @kb.add("c-s-right", filter=is_input)
    def _form_select_word_right(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.WORD_NEXT, shift=True)

    @kb.add("c-a", filter=is_input)
    @kb.add("home", filter=is_input)
    def _form_line_home(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.LINE_HOME)

    @kb.add("c-e", filter=is_input)
    @kb.add("end", filter=is_input)
    def _form_line_end(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.LINE_END)

    @kb.add("s-home", filter=is_input)
    def _form_select_line_home(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.LINE_HOME, shift=True)

    @kb.add("s-end", filter=is_input)
    def _form_select_line_end(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.LINE_END, shift=True)

    @kb.add("c-v", filter=is_input)
    def _form_paste_clipboard(event):
        form = state.form
        if form is None:
            return
        text = _read_clipboard_text(event)
        if text:
            form.handle_intent(InputIntent.PASTE, text)

    @kb.add("<bracketed-paste>", filter=is_input)
    def _form_bracketed_paste(event):
        form = state.form
        if form is None:
            return
        payload = event.data or ""
        if payload:
            form.handle_intent(InputIntent.PASTE, payload)

    @kb.add("backspace", filter=is_input)
    def _form_backspace(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.BACKSPACE)

    @kb.add("space", filter=is_input)
    def _form_space(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.SPACE)

    @kb.add("+", filter=is_input)
    @kb.add("=", filter=is_input)
    def _form_inc(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.INC, event.data or "+")

    @kb.add("-", filter=is_input)
    def _form_dec(event):
        form = state.form
        if form is None:
            return
        form.handle_intent(InputIntent.DEC)

    @kb.add("<any>", filter=is_input)
    def _form_any_key(event):
        form = state.form
        if form is None:
            return
        char = event.data
        if not char:
            return
        # Multi-char payloads (some paste paths) go through PASTE.
        if len(char) > 1:
            form.handle_intent(InputIntent.PASTE, char)
            return
        form.handle_intent(InputIntent.CHAR, char)

    # -- Layout --

    title_bar = Window(
        content=FormattedTextControl(get_title_content, show_cursor=False),
        height=1,
        style="class:title",
    )
    title_bar_container = ConditionalContainer(title_bar, filter=~is_zen_layout)

    main_window = Window(
        content=FormattedTextControl(get_main_content),
        wrap_lines=False,
    )

    separator = Window(height=1, char="─", style="class:separator")

    status_bar = Window(
        content=FormattedTextControl(get_status_content, show_cursor=False),
        height=1,
    )

    # Form input display (inline editing via FormattedTextControl)
    def _get_form_height() -> int:
        session = state.input_session
        if session is None:
            return 1
        lines = render_input_form_lines(
            session.form,
            mode_label=session.mode_label,
            entity_label=session.entity_type.value.title(),
            width=_terminal_cols(),
        )
        return max(1, len(lines))

    form_display = ConditionalContainer(
        Window(
            content=FormattedTextControl(get_form_content),
            height=_get_form_height,
        ),
        filter=is_input,
    )

    layout = Layout(
        HSplit([
            title_bar_container,
            main_window,
            separator,
            status_bar,
            form_display,
        ])
    )

    # -- Run --

    app = Application(
        layout=layout,
        key_bindings=kb,
        style=APP_STYLE,
        full_screen=True,
    )
    # Shorten escape/prefix timeouts so ESC triggers quickly (default 1s is too slow).
    # Alt+Up/Down still work: user has ~50ms to press the second key.
    app.ttimeoutlen = 0.05
    app.timeoutlen = 0.05

    def _set_now_result(result: Result) -> None:
        state.last_result = result

    async def _run_async() -> None:
        asyncio.create_task(
            run_timer_runtime(
                now=state.now,
                app=app,
                on_result=_set_now_result,
            )
        )
        await app.run_async()

    asyncio.run(_run_async())
