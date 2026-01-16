import asyncio
import subprocess
import sys
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition

from mukitodo.actions import Result
from mukitodo.tui.states.box_state import BoxSubview

from .states.app_state import AppState, UIMode, View, ConfirmAction
from .states.now_state import TimerStateEnum, TimerEventEnum
from .states.input_state import InputPurpose
from .renderer import Renderer, LayoutManager


def _activate_iterm2_macos() -> None:
    """
    Best-effort bring iTerm2 to the foreground on macOS.

    Spec requires only bringing the app to front (no specific window/tab).
    We try both application names: "iTerm" and "iTerm2".
    """
    scripts = [
        'tell application "iTerm" to activate',
        'tell application "iTerm2" to activate',
    ]
    for script in scripts:
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            break
        except Exception:
            continue


def _bell(app: Application) -> None:
    """Best-effort terminal bell (no external deps)."""
    try:
        app.output.bell()
        return
    except Exception:
        pass
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        return


def run():
    state = AppState()
    renderer = Renderer(state)
    layout_manager = LayoutManager(state=state, renderer=renderer)

    # ========================================
    # Key Bindings
    # ========================================
    kb = KeyBindings()

    is_normal_mode = Condition(lambda: state.ui_mode == UIMode.NORMAL)
    is_command_mode = Condition(lambda: state.ui_mode == UIMode.COMMAND)
    is_input_mode = Condition(lambda: state.ui_mode == UIMode.INPUT)
    is_confirm_mode = Condition(lambda: state.ui_mode == UIMode.CONFIRM)

    is_now_view = Condition(lambda: state.view == View.NOW)
    is_structure_view = Condition(lambda: state.view == View.STRUCTURE)
    is_info_view = Condition(lambda: state.view == View.INFO)
    is_archive_view = Condition(lambda: state.view == View.ARCHIVE)
    is_timeline_view = Condition(lambda: state.view == View.TIMELINE)
    is_box_view = Condition(lambda: state.view == View.BOX)

    is_input_text_field = Condition(lambda: state.ui_mode == UIMode.INPUT and state.input_state.is_text_input_field())
    is_input_non_text_field = Condition(lambda: state.ui_mode == UIMode.INPUT and (not state.input_state.is_text_input_field()))

    def _safe_add(*primary_keys: str, fallback_keys: tuple[str, ...] | None = None, filter=None):
        """
        Register key bindings with a fallback for older prompt-toolkit key names.

        Many terminals send Alt+Arrow as an ESC-prefixed sequence, so we fallback
        to ("escape","up/down") when "m-up"/"m-down" isn't supported.
        """
        try:
            return kb.add(*primary_keys, filter=filter)
        except ValueError:
            if not fallback_keys:
                raise
            return kb.add(*fallback_keys, filter=filter)


    # == General Key Bindings ==

    @kb.add("c-c")
    @kb.add("c-d")
    def _(event):
        event.app.exit()

    # == Normal Mode Key Bindings ==

    @kb.add("q", filter=is_normal_mode & (is_now_view | is_structure_view))
    def _(event):
        state.ask_confirm(ConfirmAction.QUIT)

    @kb.add("q", filter=is_normal_mode & (is_timeline_view | is_box_view | is_archive_view | is_info_view))
    def _(event):
        state.exit_current_view()

    @kb.add("tab", filter=is_normal_mode & ~is_info_view)
    def _(event):
        if state.view in (View.NOW, View.STRUCTURE):
            state.switch_view()
        else:
            state.return_to_last_primary_view()

    @kb.add("[", filter=is_normal_mode & ~is_info_view)
    def _(event):
        state.toggle_box_view(BoxSubview.TODOS)

    @kb.add("]", filter=is_normal_mode & ~is_info_view)
    def _(event):
        state.toggle_box_view(BoxSubview.IDEAS)

    @kb.add("`", filter=is_normal_mode & ~is_info_view)
    def _(event):
        if state.view == View.ARCHIVE:
            state.exit_archive_view()
        else:
            state.enter_archive_view()

    @kb.add("'", filter=is_normal_mode & ~is_info_view)
    def _(event):
        if state.view == View.TIMELINE:
            state.exit_timeline_view()
        else:
            state.enter_timeline_view()


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

    @_safe_add("m-up", fallback_keys=("escape", "up"), filter=is_normal_mode & is_structure_view)
    def _(event):
        state.structure_state.move_selected_item_order(-1)

    @_safe_add("m-down", fallback_keys=("escape", "down"), filter=is_normal_mode & is_structure_view)
    def _(event):
        state.structure_state.move_selected_item_order(1)
    @kb.add("right", filter=is_normal_mode & is_structure_view)
    def _(event):
        if state.has_pending_transfer():
            state.handle_structure_right_for_transfer()
            return
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
        state.start_input(InputPurpose.ADD)
        if state.ui_mode == UIMode.INPUT:
            layout_manager.sync_all_text_buffers_from_state()
            layout_manager.focus_current_field(event.app.layout)

    @kb.add("r", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.start_input(InputPurpose.EDIT)
        if state.ui_mode == UIMode.INPUT:
            layout_manager.sync_all_text_buffers_from_state()
            layout_manager.focus_current_field(event.app.layout)
    
    @kb.add("backspace", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.ask_confirm(ConfirmAction.DELETE_STRUCTURE_ITEM)

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

    @kb.add("p", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.structure_state.toggle_pin_selected_item()

    @kb.add("a", filter=is_normal_mode & is_structure_view)
    def _(event):
        state.ask_confirm(ConfirmAction.ARCHIVE_STRUCTURE_ITEM)

    @kb.add("enter", filter=is_normal_mode & is_structure_view)
    def _(event):
        if state.has_pending_transfer():
            state.ask_confirm(ConfirmAction.CONFIRM_BOX_TRANSFER)
            return
        state.ask_confirm(ConfirmAction.ENTER_NOW_WITH_STRUCTURE_ITEM)

    @kb.add("escape", filter=is_normal_mode & is_structure_view)
    def _(event):
        if state.has_pending_transfer():
            state.cancel_pending_transfer()
            return

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
        state.ask_confirm(ConfirmAction.FINISH_SESSION)

    # Normal Mode & BOX View

    @kb.add("up", filter=is_normal_mode & is_box_view)
    def _(event):
        state.box_state.move_cursor(-1)

    @kb.add("down", filter=is_normal_mode & is_box_view)
    def _(event):
        state.box_state.move_cursor(1)

    @_safe_add("m-up", fallback_keys=("escape", "up"), filter=is_normal_mode & is_box_view)
    def _(event):
        state.box_state.move_selected_item_order(-1)

    @_safe_add("m-down", fallback_keys=("escape", "down"), filter=is_normal_mode & is_box_view)
    def _(event):
        state.box_state.move_selected_item_order(1)

    @kb.add("i", filter=is_normal_mode & is_box_view)
    def _(event):
        state.open_item_info()

    @kb.add("=", filter=is_normal_mode & is_box_view)
    @kb.add("+", filter=is_normal_mode & is_box_view)
    def _(event):
        state.start_input(InputPurpose.ADD)
        if state.ui_mode == UIMode.INPUT:
            layout_manager.sync_all_text_buffers_from_state()
            layout_manager.focus_current_field(event.app.layout)

    @kb.add("r", filter=is_normal_mode & is_box_view)
    def _(event):
        state.start_input(InputPurpose.EDIT)
        if state.ui_mode == UIMode.INPUT:
            layout_manager.sync_all_text_buffers_from_state()
            layout_manager.focus_current_field(event.app.layout)

    @kb.add("backspace", filter=is_normal_mode & is_box_view)
    def _(event):
        state.ask_confirm(ConfirmAction.DELETE_BOX_ITEM)

    @kb.add("a", filter=is_normal_mode & is_box_view)
    def _(event):
        state.ask_confirm(ConfirmAction.ARCHIVE_BOX_ITEM)

    @kb.add("m", filter=is_normal_mode & is_box_view)
    def _(event):
        if state.box_state.subview == BoxSubview.TODOS:
            state.start_pending_move_from_box()
        else:
            state.start_pending_promote_from_box()

    @kb.add("escape", filter=is_normal_mode & is_box_view)
    def _(event):
        state.exit_box_view()

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

    # ARCHIVE view specific key bindings

    @kb.add("up", filter=is_normal_mode & is_archive_view)
    def _(event):
        state.archive_state.move_cursor(-1)

    @kb.add("down", filter=is_normal_mode & is_archive_view)
    def _(event):
        state.archive_state.move_cursor(1)

    @kb.add("a", filter=is_normal_mode & is_archive_view)
    def _(event):
        """Unarchive selected item."""
        state.ask_confirm(ConfirmAction.UNARCHIVE_ITEM)

    @kb.add("backspace", filter=is_normal_mode & is_archive_view)
    def _(event):
        """Delete selected item permanently."""
        state.ask_confirm(ConfirmAction.DELETE_ARCHIVE_ITEM)

    @kb.add("i", filter=is_normal_mode & is_archive_view)
    def _(event):
        """View info of selected archived item."""
        state.open_item_info()

    @kb.add("escape", filter=is_normal_mode & is_archive_view)
    @kb.add("`", filter=is_normal_mode & is_archive_view)
    def _(event):
        """Exit Archive View (return to STRUCTURE)."""
        state.exit_archive_view()

    # TIMELINE view key bindings

    @kb.add("escape", filter=is_normal_mode & is_timeline_view)
    def _(event):
        """Exit Timeline View."""
        state.exit_timeline_view()

    @kb.add("up", filter=is_normal_mode & is_timeline_view)
    def _(event):
        state.timeline_state.move_cursor(-1)

    @kb.add("down", filter=is_normal_mode & is_timeline_view)
    def _(event):
        state.timeline_state.move_cursor(1)

    @kb.add("i", filter=is_normal_mode & is_timeline_view)
    def _(event):
        """View details of selected session."""
        state.open_item_info()

    @kb.add("backspace", filter=is_normal_mode & is_timeline_view)
    def _(event):
        """Delete selected session."""
        state.ask_confirm(ConfirmAction.DELETE_TIMELINE_ITEM)


    # == Input Mode Key Bindings (README Form Input) ==

    @kb.add("tab", filter=is_input_mode)
    def _(event):
        layout_manager.save_current_text_field_to_state()
        state.input_state.move_to_next_field()
        layout_manager.focus_current_field(event.app.layout)

    @kb.add("s-tab", filter=is_input_mode)
    def _(event):
        layout_manager.save_current_text_field_to_state()
        state.input_state.move_to_prev_field()
        layout_manager.focus_current_field(event.app.layout)

    @kb.add("escape", filter=is_input_mode)
    @kb.add("c-g", filter=is_input_mode)
    def _(event):
        state.cancel_input()
        layout_manager.reset_buffers()

    @kb.add("enter", filter=is_input_mode)
    def _(event):
        layout_manager.save_current_text_field_to_state()
        state.confirm_input()
        if state.ui_mode == UIMode.INPUT:
            layout_manager.sync_all_text_buffers_from_state()
            layout_manager.focus_current_field(event.app.layout)
        else:
            layout_manager.reset_buffers()

    @kb.add("space", filter=is_input_mode & is_input_non_text_field)
    def _(event):
        state.input_state.edit_field_value(direction=None, value=None)

    @kb.add("+", filter=is_input_mode & is_input_non_text_field)
    @kb.add("=", filter=is_input_mode & is_input_non_text_field)
    def _(event):
        state.input_state.edit_field_value(direction=1, value=None)

    @kb.add("-", filter=is_input_mode & is_input_non_text_field)
    def _(event):
        state.input_state.edit_field_value(direction=-1, value=None)

    @kb.add("up", filter=is_input_mode & is_input_non_text_field)
    def _(event):
        state.input_state.edit_field_value(direction=1, value=None)

    @kb.add("down", filter=is_input_mode & is_input_non_text_field)
    def _(event):
        state.input_state.edit_field_value(direction=-1, value=None)

    # In text fields, Up/Down should be no-op (v1 single-line; avoid accidental edits/scroll semantics).
    @kb.add("up", filter=is_input_mode & is_input_text_field)
    def _(event):
        return

    @kb.add("down", filter=is_input_mode & is_input_text_field)
    def _(event):
        return


    # == Confirm Mode Key Bindings ==

    def _confirm_finish_session(event) -> None:
        """
        Confirm handler for NOW finish-session flow.
        Keep legacy behavior: if finishing a session enters INPUT mode, we immediately
        sync buffers and focus the current field.
        """
        state.finish_session()
        if state.ui_mode == UIMode.INPUT:
            layout_manager.sync_all_text_buffers_from_state()
            layout_manager.focus_current_field(event.app.layout)

    _confirm_handlers = {
        ConfirmAction.QUIT: lambda e: e.app.exit(),
        ConfirmAction.DELETE_STRUCTURE_ITEM: lambda e: state.structure_state.delete_selected_item(),
        ConfirmAction.ARCHIVE_STRUCTURE_ITEM: lambda e: state.structure_state.archive_selected_item(),
        ConfirmAction.DELETE_BOX_ITEM: lambda e: state.box_state.delete_selected_item(),
        ConfirmAction.ARCHIVE_BOX_ITEM: lambda e: state.box_state.archive_selected_item(),
        ConfirmAction.ENTER_NOW_WITH_STRUCTURE_ITEM: lambda e: state.enter_now_with_structure_item(),
        ConfirmAction.CONFIRM_BOX_TRANSFER: lambda e: state.confirm_pending_transfer_in_structure(),
        ConfirmAction.FINISH_SESSION: _confirm_finish_session,
        ConfirmAction.UNARCHIVE_ITEM: lambda e: state.unarchive_item_and_maybe_jump(),
        ConfirmAction.DELETE_ARCHIVE_ITEM: lambda e: state.archive_state.delete_selected_item(),
        ConfirmAction.DELETE_TIMELINE_ITEM: lambda e: state.timeline_state.delete_selected_item(),
    }

    @kb.add("enter", filter=is_confirm_mode)
    @kb.add("backspace", filter=is_confirm_mode)
    @kb.add("up", filter=is_confirm_mode)
    @kb.add("down", filter=is_confirm_mode)
    @kb.add("left", filter=is_confirm_mode)
    @kb.add("right", filter=is_confirm_mode)
    @kb.add("<any>", filter=is_confirm_mode)
    def _(event):
        """
        Single confirm dispatcher:
        - Press the same key again to confirm.
        - Any other key cancels.

        View is intentionally ignored: we only use state.confirm_action.
        """
        confirm_action = state.confirm_action
        if confirm_action is None:
            state.exit_confirm()
            return

        def _normalize_confirm_key(key: str) -> str:
            """
            Normalize prompt-toolkit key strings for confirm matching.

            Some terminals report Enter/Backspace as control sequences:
            - Enter: "c-m"
            - Backspace: "c-h"
            We canonicalize these to match ConfirmAction.key values ("enter"/"backspace").
            """
            return {
                "c-m": "enter",
                "c-h": "backspace",
            }.get(key, key)

        # Guard: <any> may occasionally provide an empty key_sequence.
        if not event.key_sequence:
            state.exit_confirm()
            return

        pressed_key = _normalize_confirm_key(event.key_sequence[0].key)
        expected_key = _normalize_confirm_key(confirm_action.key)
        if pressed_key == expected_key:
            handler = _confirm_handlers.get(confirm_action)
            if handler is not None:
                handler(event)

        state.exit_confirm()

    # == Command Mode Key Bindings ==

    # TODO: Command Mode Key Bindings


    layout = layout_manager.build_layout()
    style = renderer.build_style()

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
            if state.now_state.timer_state == TimerStateEnum.RUNNING:
                # Only invalidate if timer seconds actually changed
                if state.now_state.update_timer():
                    app.invalidate()

            # Consume one-shot timer events regardless of view/mode.
            timer_event = state.now_state.consume_timer_event()
            if timer_event is None:
                continue

            _bell(app)

            if timer_event == TimerEventEnum.WORK_5MIN_LEFT:
                # Subtle: no foreground activation.
                state.message.set(Result(True, None, "5 minutes left"))
                app.invalidate()
                continue

            if timer_event == TimerEventEnum.WORK_TIME_UP:
                _activate_iterm2_macos()
                state.message.set(Result(True, None, "Time's up (00:00). Press Enter to finish session, or r to reset"))
                # Auto-enter confirm; user can cancel and re-enter later via Enter.
                state.ask_confirm(ConfirmAction.FINISH_SESSION)
                app.invalidate()
                continue

            if timer_event == TimerEventEnum.BREAK_TIME_UP:
                state.message.set(Result(True, None, "Break time is over"))
                app.invalidate()
                continue
    
    # Run app with async timer
    async def run_async():
        asyncio.create_task(update_timer_loop())
        await app.run_async()
    
    asyncio.run(run_async())
