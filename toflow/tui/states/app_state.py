from enum import Enum
from toflow import actions
from toflow.actions import Result, EmptyResult
from toflow.tui.states.message_holder import MessageHolder

from toflow.tui.states.now_state import NowState
from toflow.tui.states.structure_state import StructureState, StructureLevel
from toflow.tui.states.info_state import InfoState
from toflow.tui.states.archive_state import ArchiveState
from toflow.tui.states.timeline_state import TimelineState
from toflow.tui.states.box_state import BoxState, BoxSubview

from toflow.tui.states.input_state import FormType, InputPurpose, InputState
from toflow.tui.states.input_state import FormField


class View(Enum):
    """View of the TUI."""
    NOW = "now"
    STRUCTURE = "structure"
    BOX = "box"
    INFO = "info"
    ARCHIVE = "archive"
    TIMELINE = "timeline"


class UIMode(Enum):
    """Mode of the TUI."""
    NORMAL = "normal"
    COMMAND = "command"
    INPUT = "input"
    CONFIRM = "confirm"

class ConfirmAction(Enum):
    """Action to be confirmed by the user."""
    QUIT = ("quit", "q")
    DELETE_STRUCTURE_ITEM = ("delete_structure_item", "backspace")
    ENTER_NOW_WITH_STRUCTURE_ITEM = ("enter_now_with_structure_item", "enter")
    FINISH_SESSION = ("finish_session", "enter")
    ARCHIVE_STRUCTURE_ITEM = ("archive_structure_item", "a")
    ARCHIVE_BOX_ITEM = ("archive_box_item", "a")
    DELETE_BOX_ITEM = ("delete_box_item", "backspace")
    CONFIRM_BOX_TRANSFER = ("confirm_box_transfer", "enter")
    CONFIRM_STRUCTURE_MOVE = ("confirm_structure_move", "enter")
    UNARCHIVE_ITEM = ("unarchive_item", "a")
    DELETE_ARCHIVE_ITEM = ("delete_archive_item", "backspace")
    DELETE_TIMELINE_ITEM = ("delete_timeline_item", "backspace")

    @property
    def name(self) -> str:
        return self.value[0]
    @property
    def key(self) -> str:
        return self.value[1]



# class BoxType(Enum):
#     """Type of the Box."""
#     TODOS = "todos"
#     IDEAS = "ideas"


class AppState:
    """TUI application state management.
    Methods:
    - "start_xxx": Start a new operation, enter the corresponding UI mode
    - "some_action(..., ask_confirm)": The action will be executed twice with confirmation
    Generally, a method is corresponding to a key binding event.
    """
    
    def __init__(self):
        # Shared message holder
        self._message = MessageHolder()
        
        # === View state ===
        self._view: View = View.NOW
        self._last_primary_view: View = View.NOW
        self._info_from_view: View | None = None
        self._timeline_from_view: View | None = None
        self._archive_from_view: View | None = None
        self._box_from_view: View | None = None  # Remember where we came from when entering BOX

        self._now_state = NowState(self._message)
        self._structure_state = StructureState(self._message)
        self._box_state = BoxState(self._message)
        self._info_state = InfoState(self._message)
        self._archive_state = ArchiveState(self._message)
        self._timeline_state = TimelineState(self._message)

        # === UI Mode state ===
        self._ui_mode = UIMode.NORMAL
        self._input_state: InputState = InputState()
        self._confirm_action: ConfirmAction | None = None

        # === BOX transfer state ===
        # None means no pending transfer. When set, STRUCTURE Enter/Esc are intercepted.
        self._pending_transfer: dict | None = None


    # == View State Management ==================================================

    def _set_view(self, view: View) -> None:
        self._view = view
        if view in (View.NOW, View.STRUCTURE):
            self._last_primary_view = view

    def switch_view(self) -> None:
        """Switch between NOW and STRUCTURE views."""
        if self._view == View.NOW:
            self._set_view(View.STRUCTURE)
        elif self._view == View.STRUCTURE:
            self._set_view(View.NOW)

    def return_to_last_primary_view(self) -> None:
        """Return to the last primary view (NOW/STRUCTURE)."""
        if self._view == View.TIMELINE:
            self._timeline_from_view = None
        elif self._view == View.BOX:
            self._box_from_view = None
        elif self._view == View.ARCHIVE:
            self._archive_from_view = None

        self._set_view(self._last_primary_view)
        if self._view == View.STRUCTURE:
            self._structure_state.load_current_lists()
        self._message.set(EmptyResult)

    def exit_current_view(self) -> None:
        """Exit current view (for Esc/q behavior in non-primary views)."""
        if self._view == View.INFO:
            self.return_from_info()
            return
        if self._view == View.TIMELINE:
            self.exit_timeline_view()
            return
        if self._view == View.BOX:
            self.exit_box_view()
            return
        if self._view == View.ARCHIVE:
            self.exit_archive_view()
            return

    # == Box View ==

    def toggle_box_view(self, subview: BoxSubview | None = None) -> None:
        """Enter or exit BOX view (optionally select subview)."""
        if self._view == View.BOX:
            if subview is not None and self._box_state.subview != subview:
                self._box_state.set_subview(subview)
                self._message.set(EmptyResult)
                return
            self.exit_box_view()
            return
        self.enter_box_view(subview=subview)

    def enter_box_view(self, *, subview: BoxSubview | None = None) -> None:
        """Enter BOX view from any non-INFO view."""
        if self._view == View.INFO:
            # Keep INFO read-only and isolated.
            self._message.set(Result(False, None, "Cannot enter BOX from INFO view"))
            return

        self._box_from_view = self._view
        self._set_view(View.BOX)
        self._box_state.set_subview(subview or BoxSubview.TODOS)
        self._box_state.load_box_lists()
        self._message.set(EmptyResult)

    def exit_box_view(self) -> None:
        """Exit BOX view and return to the previous view (NOW/STRUCTURE)."""
        target = self._box_from_view or View.STRUCTURE
        self._box_from_view = None
        self._set_view(target)
        if self._view == View.STRUCTURE:
            self._structure_state.load_current_lists()
        self._message.set(EmptyResult)

    # == Box Transfer (v1) ==

    def has_pending_transfer(self) -> bool:
        """Whether a BOX->STRUCTURE or STRUCTURE->STRUCTURE transfer is pending."""
        return self._pending_transfer is not None

    def get_pending_transfer_hint(self) -> str | None:
        """Get the hint message for current pending transfer, or None if no transfer."""
        if self._pending_transfer is None:
            return None
        kind = str(self._pending_transfer.get("kind") or "")
        hints = {
            "move_box_todo": "Move: select a project (→) or enter Todos level (→), then press Enter to confirm",
            "promote_idea": "Promote: select a track, then press Enter to confirm",
            "move_structure_project": "Move Project: select a track, then press Enter to confirm",
            "move_structure_todo": "Move Todo: select a project (→), then press Enter to confirm",
        }
        return hints.get(kind)

    def refresh_pending_transfer_hint(self) -> None:
        """Refresh the hint message for pending transfer (call after navigation)."""
        hint = self.get_pending_transfer_hint()
        if hint:
            self._message.set(Result(True, None, hint))

    def start_pending_move_from_box(self) -> None:
        """Start BOX todo move flow (BOX Todos -> select Project in STRUCTURE -> Enter confirm)."""
        if self._view != View.BOX:
            return
        if self._box_state.subview != BoxSubview.TODOS:
            self._message.set(Result(False, None, "Switch to TODOS to move a box todo"))
            return

        item_type, item_id = self._box_state.get_selected_item_context()
        if item_type != "todo" or item_id is None:
            self._message.set(Result(False, None, "No box todo selected"))
            return

        self._pending_transfer = {
            "kind": "move_box_todo",
            "item_id": item_id,
            "return_box_subview": BoxSubview.TODOS,
        }
        self._set_view(View.STRUCTURE)
        self._structure_state.reset_to_default_view()
        self.refresh_pending_transfer_hint()

    def start_pending_promote_from_box(self) -> None:
        """Start BOX idea promote flow (BOX Ideas -> select Track in STRUCTURE -> Enter confirm)."""
        if self._view != View.BOX:
            return
        if self._box_state.subview != BoxSubview.IDEAS:
            self._message.set(Result(False, None, "Switch to IDEAS to promote an idea"))
            return

        item_type, item_id = self._box_state.get_selected_item_context()
        if item_type != "idea" or item_id is None:
            self._message.set(Result(False, None, "No idea selected"))
            return

        # Guard: already promoted ideas cannot be promoted again.
        idea_result = actions.get_idea_item_dict(item_id)
        if idea_result.success and idea_result.data:
            if str(idea_result.data.get("status") or "") == "promoted":
                self._message.set(Result(False, None, "Idea is already promoted"))
                return

        self._pending_transfer = {
            "kind": "promote_idea",
            "item_id": item_id,
            "return_box_subview": BoxSubview.IDEAS,
        }
        self._set_view(View.STRUCTURE)
        self._structure_state.reset_to_default_view()
        self.refresh_pending_transfer_hint()

    def cancel_pending_transfer(self) -> None:
        """Cancel a pending BOX/STRUCTURE transfer."""
        if self._pending_transfer is None:
            return

        kind = str(self._pending_transfer.get("kind") or "")

        # Structure move: just clear state and stay in STRUCTURE
        if kind in ("move_structure_project", "move_structure_todo"):
            self._pending_transfer = None
            self._structure_state.load_current_lists()
            self._message.set(EmptyResult)
            return

        # BOX transfer: return to BOX view
        return_subview = self._pending_transfer.get("return_box_subview") or BoxSubview.TODOS
        # Exit special no-cursor TODOS confirm state (go back once).
        if self._structure_state.structure_level == StructureLevel.TODOS:
            self._structure_state.go_back()
        self._pending_transfer = None
        self._set_view(View.BOX)
        self._box_state.set_subview(return_subview)
        self._box_state.load_box_lists()
        self._message.set(EmptyResult)

    def start_pending_move_from_structure(self) -> None:
        """Start STRUCTURE item move flow (Project → Track, Todo → Project)."""
        if self._view != View.STRUCTURE:
            return

        item_type, track_id, project_id, todo_id = self._structure_state.get_selected_item_context()

        if item_type == "project" and project_id is not None:
            self._pending_transfer = {
                "kind": "move_structure_project",
                "item_id": project_id,
            }
            self._structure_state.reset_to_default_view()
            self.refresh_pending_transfer_hint()
            return

        if item_type == "todo" and todo_id is not None:
            self._pending_transfer = {
                "kind": "move_structure_todo",
                "item_id": todo_id,
            }
            self._structure_state.reset_to_default_view()
            self.refresh_pending_transfer_hint()
            return

        self._message.set(Result(False, None, "Select a project or todo to move"))

    def confirm_pending_transfer_in_structure(self) -> None:
        """Confirm pending transfer in STRUCTURE (invoked by STRUCTURE Enter)."""
        if self._pending_transfer is None:
            return
        if self._view != View.STRUCTURE:
            return

        kind = str(self._pending_transfer.get("kind") or "")
        item_id = self._pending_transfer.get("item_id")
        if not isinstance(item_id, int):
            self._pending_transfer = None
            self._message.set(Result(False, None, "Invalid pending transfer"))
            return

        if kind == "move_box_todo":
            item_type, _, project_id, _ = self._structure_state.get_selected_item_context()
            # Accept confirmation in:
            # - TRACKS_WITH_PROJECTS_P (item_type == "project")
            # - TODOS (item_type == "todo" but project_id is set; todo cursor may be None)
            if project_id is None:
                self._message.set(Result(False, None, "Move: select a project first"))
                return
            result = actions.move_todo_to_project(item_id, project_id)
            self._message.set(result)
            if not result.success:
                return

            self._pending_transfer = None
            # Exit special no-cursor TODOS confirm state (go back once).
            self._structure_state.go_back()
            self._set_view(View.BOX)
            self._box_state.set_subview(BoxSubview.TODOS)
            self._box_state.load_box_lists()
            return

        if kind == "promote_idea":
            item_type, track_id, _, _ = self._structure_state.get_selected_item_context()
            if item_type != "track" or track_id is None:
                self._message.set(Result(False, None, "Select a track to promote the idea into"))
                return
            result = actions.promote_idea_item_to_project(item_id, track_id)
            self._message.set(result)
            if not result.success:
                return

            self._pending_transfer = None
            self._set_view(View.BOX)
            self._box_state.set_subview(BoxSubview.IDEAS)
            self._box_state.load_box_lists()
            return

        if kind == "move_structure_project":
            item_type, target_track_id, _, _ = self._structure_state.get_selected_item_context()
            if target_track_id is None:
                self._message.set(Result(False, None, "Select a track first"))
                return
            result = actions.move_project_to_track(item_id, target_track_id)
            self._message.set(result)
            if result.success:
                self._pending_transfer = None
                self._structure_state.load_current_lists()
            return

        if kind == "move_structure_todo":
            item_type, _, target_project_id, _ = self._structure_state.get_selected_item_context()
            if target_project_id is None:
                self._message.set(Result(False, None, "Select a project first"))
                return
            result = actions.move_todo_to_project(item_id, target_project_id)
            self._message.set(result)
            if result.success:
                self._pending_transfer = None
                self._structure_state.load_current_lists()
            return

        self._message.set(Result(False, None, f"Unknown transfer kind: {kind}"))


    def handle_structure_right_for_transfer(self) -> None:
        """
        Handle Right Arrow in STRUCTURE when a transfer is pending.

        - For move_box_todo / move_structure_todo:
          - In TRACKS_WITH_PROJECTS_P level, Right Arrow enters TODOS level *without* selecting a todo,
            and shows a hint to press Enter to confirm.
          - Otherwise, fall back to normal select_current navigation.
        - For promote_idea / move_structure_project:
          - Stay at track level, enter confirm mode.
        """
        if self._view != View.STRUCTURE:
            return
        if self._pending_transfer is None:
            self._structure_state.select_current()
            return

        kind = str(self._pending_transfer.get("kind") or "")

        # move_box_todo / move_structure_todo: can confirm at project level or enter todos level
        if kind in ("move_box_todo", "move_structure_todo"):
            if self._structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
                self._structure_state.select_current(enter_todos_level_without_cursor=True)
                # Enter confirm mode immediately when entering TODOS level for move.
                confirm_action = ConfirmAction.CONFIRM_STRUCTURE_MOVE if kind == "move_structure_todo" else ConfirmAction.CONFIRM_BOX_TRANSFER
                self.ask_confirm(confirm_action)
                return
            # Otherwise navigate normally but keep hint
            self._structure_state.select_current()
            self.refresh_pending_transfer_hint()
            return

        # promote_idea / move_structure_project: confirm at track level
        if kind in ("promote_idea", "move_structure_project"):
            # Can navigate to see tracks, but confirm happens at track level
            if self._structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS_T:
                confirm_action = ConfirmAction.CONFIRM_STRUCTURE_MOVE if kind == "move_structure_project" else ConfirmAction.CONFIRM_BOX_TRANSFER
                self.ask_confirm(confirm_action)
                return
            # Navigate normally but keep hint
            self._structure_state.select_current()
            self.refresh_pending_transfer_hint()
            return

        self._structure_state.select_current()

    # == Info View ==

    def open_item_info(self) -> None:
        """Open INFO view for currently selected item."""
        if self._view == View.INFO:
            raise ValueError("Already in INFO view")

        # Save current view for returning
        self._info_from_view = self._view

        # Get current item context based on view
        if self._view == View.NOW:
            item_type, track_id, project_id, todo_id = self._now_state.get_current_item_context()
        elif self._view == View.STRUCTURE:
            item_type, track_id, project_id, todo_id = self._structure_state.get_selected_item_context()
        elif self._view == View.ARCHIVE:
            item_type, track_id, project_id, todo_id = self._archive_state.get_selected_item_context()
        elif self._view == View.BOX:
            item_type, item_id = self._box_state.get_selected_item_context()
            if item_type == "none" or item_id is None:
                self._message.set(Result(False, None, "No item selected"))
                return
            self._set_view(View.INFO)
            self._info_state.reload_info_panel_for_box(item_type, item_id)
            return
        elif self._view == View.TIMELINE:
            # For Timeline view, get the selected session
            item_info = self._timeline_state.get_selected_item_id()
            if item_info is None:
                self._message.set(Result(False, None, "No item selected"))
                return
            item_type, item_id = item_info
            self._set_view(View.INFO)
            self._info_state.reload_info_panel_for_timeline(item_type, item_id)
            return
        else:
            return

        if item_type == "none":
            return
        if item_type == "track" and track_id is None:
            self._message.set(Result(False, None, "No track selected"))
            return
        if item_type == "project" and project_id is None:
            self._message.set(Result(False, None, "No project selected"))
            return
        if item_type == "todo" and todo_id is None:
            self._message.set(Result(False, None, "No todo selected"))
            return

        self._set_view(View.INFO)
        self._info_state.reload_info_panel(item_type, track_id, project_id, todo_id)

    def return_from_info(self) -> None:
        """Return from INFO view to previous view."""
        if self._info_from_view is None:
            return

        self._set_view(self._info_from_view)
        self._info_from_view = None
        self._info_state.leave_info_panel()
        if self._view == View.STRUCTURE:
            self._structure_state.load_current_lists()
        elif self._view == View.ARCHIVE:
            self._archive_state.load_archive_data()
        elif self._view == View.TIMELINE:
            self._timeline_state.load_timeline_data()
        elif self._view == View.BOX:
            self._box_state.load_box_lists()

    # == Archive View ==

    def enter_archive_view(self) -> None:
        """Enter ARCHIVE view from any view."""
        if self._view == View.INFO:
            self._message.set(Result(False, None, "Cannot enter ARCHIVE from INFO view"))
            return
        self._archive_from_view = self._view
        self._set_view(View.ARCHIVE)
        self._archive_state.load_archive_data()

    def exit_archive_view(self) -> None:
        """Exit ARCHIVE view and return to previous view."""
        target = self._archive_from_view or View.STRUCTURE
        self._archive_from_view = None
        self._set_view(target)
        if self._view == View.STRUCTURE:
            self._structure_state.load_current_lists()
        elif self._view == View.BOX:
            self._box_state.load_box_lists()
        elif self._view == View.TIMELINE:
            self._timeline_state.load_timeline_data()

    def unarchive_item_and_maybe_jump(self) -> None:
        """
        Unarchive the selected item in ARCHIVE view.

        Special behavior (README): if the unarchived item is a Box Todo, jump to BOX Todos.
        """
        if self._view != View.ARCHIVE:
            return

        self._archive_state.unarchive_selected_item()

        last_result = self._message.last_result
        if last_result.success and self._archive_state.last_unarchived_was_box_todo:
            self._set_view(View.BOX)
            self._box_state.set_subview(BoxSubview.TODOS)
            self._box_state.load_box_lists()

    # == Timeline View ==

    def enter_timeline_view(self) -> None:
        """Enter TIMELINE view from any non-INFO view."""
        if self._view == View.INFO:
            self._message.set(Result(False, None, "Cannot enter TIMELINE from INFO view"))
            return
        self._timeline_from_view = self._view
        self._set_view(View.TIMELINE)
        self._timeline_state.load_timeline_data()

    def exit_timeline_view(self) -> None:
        """Exit TIMELINE view and return to previous view."""
        if self._timeline_from_view is not None:
            self._set_view(self._timeline_from_view)
            self._timeline_from_view = None
        else:
            self._set_view(View.STRUCTURE)
        if self._view == View.STRUCTURE:
            self._structure_state.load_current_lists()
        elif self._view == View.BOX:
            self._box_state.load_box_lists()

    # == Now View ==

    def enter_now_with_structure_item(self) -> None:
        """Enter NOW view with currently selected structure item (project or todo)."""
        item_type, track_id, project_id, todo_id = self._structure_state.get_selected_item_context()

        if item_type not in ["project", "todo"]:
            return

        assert track_id is not None
        assert project_id is not None

        self._now_state.set_item(track_id, project_id, todo_id)
        self._set_view(View.NOW)
        self._message.set(Result(True, None, f"Entered NOW with {item_type}"))

    def finish_session(self) -> None:
        """Finish current NOW session: save to database, update todo stages (if any), then record session description."""
        # Save session to database
        result = self._now_state.save_session()
        if not result.success:
            self._message.set(result)
            return

        # If this finish was triggered after a WORK time-up (00:00 latch), arm break-after-finish.
        # Manual finishes should not arm break.
        if self._now_state.work_timeup_latched:
            self._now_state.arm_break_after_finish(5)

        # Enter INPUT mode for stage update / session description
        session_id = self._now_state.last_saved_session_id
        if session_id is None:
            self._message.set(Result(False, None, "Failed to save session: no session id"))
            return

        # If this session is on a Todo, first ask how many stages were completed, then proceed to session description.
        if self._now_state.current_todo_id is not None:
            self._ui_mode = UIMode.INPUT
            self._input_state.set_input_context(
                input_purpose=InputPurpose.ADD,
                form_type=FormType.NOW_STAGE_UPDATE,
                current_item_id=self._now_state.current_todo_id,  # todo_id for loading total/current
                context_track_id=None,
                context_project_id=None,
                context_todo_item_id=self._now_state.current_todo_id,
                context_now_session_id=session_id,
            )
            self._message.set(Result(True, None, "Session saved. How many stages completed?"))
            return

        # Otherwise: project-level session → enter session description directly.
        self._ui_mode = UIMode.INPUT
        self._input_state.set_input_context(
            input_purpose=InputPurpose.ADD,
            form_type=FormType.SESSION_DESCRIPTION,
            current_item_id=session_id,
            context_track_id=None,
            context_project_id=self._now_state.current_project_id if self._now_state.current_todo_id is None else None,
            context_todo_item_id=self._now_state.current_todo_id,
            context_now_session_id=session_id,
        )
        self._message.set(Result(True, None, "Session saved. Add session description"))

    # == UI State / Mode Management =============================================

    # == Confirm Mode ==

    def ask_confirm(self, action: ConfirmAction) -> None:
        """Enter CONFIRM mode and wait for user confirmation for the given action."""
        self._ui_mode = UIMode.CONFIRM
        self._confirm_action = action


    def exit_confirm(self) -> None:
        """
        Exit CONFIRM mode.

        Note: confirmed actions may transition the UI into another mode (e.g. INPUT).
        This method only restores NORMAL when we are still in CONFIRM.
        """
        if self._ui_mode == UIMode.CONFIRM:
            self._ui_mode = UIMode.NORMAL
        self._confirm_action = None

    # == Input Mode ==

    def start_input(self, input_purpose: InputPurpose) -> None:
        """Enter INPUT mode for a form session (README-style Input Mode)."""
        form_type: FormType | None = None
        current_item_id: int | None = None

        context_track_id: int | None = None
        context_project_id: int | None = None
        context_todo_item_id: int | None = None
        context_now_session_id: int | None = None

        if self._view == View.STRUCTURE:
            item_type, track_id, project_id, todo_id = self._structure_state.get_selected_item_context()
            context_track_id = track_id
            context_project_id = project_id
            context_todo_item_id = todo_id

            if input_purpose == InputPurpose.ADD:
                if self._structure_state.structure_level == StructureLevel.TRACKS:
                    form_type = FormType.TRACK
                elif self._structure_state.structure_level in (StructureLevel.TRACKS_WITH_PROJECTS_T, StructureLevel.TRACKS_WITH_PROJECTS_P):
                    form_type = FormType.PROJECT
                else:
                    form_type = FormType.STRUCTURE_TODO
            else:  # EDIT
                if item_type == "track":
                    form_type = FormType.TRACK
                    current_item_id = track_id
                elif item_type == "project":
                    form_type = FormType.PROJECT
                    current_item_id = project_id
                elif item_type == "todo":
                    form_type = FormType.STRUCTURE_TODO
                    current_item_id = todo_id

        elif self._view == View.BOX:
            box_subview = self._box_state.subview
            item_type, item_id = self._box_state.get_selected_item_context()

            if input_purpose == InputPurpose.ADD:
                form_type = FormType.BOX_TODO if box_subview == BoxSubview.TODOS else FormType.BOX_IDEA
            else:  # EDIT
                if item_type == "none" or item_id is None:
                    self._message.set(Result(False, None, "No item selected for edit"))
                    return
                form_type = FormType.BOX_TODO if item_type == "todo" else FormType.BOX_IDEA
                current_item_id = item_id

        elif self._view == View.INFO:
            # INFO view is read-only (editing is intentionally disabled).
            self._message.set(Result(False, None, "INFO view is read-only"))
            return

        elif self._view == View.TIMELINE:
            self._message.set(Result(False, None, "Input mode is not available in TIMELINE view"))
            return

        elif self._view == View.ARCHIVE:
            # v1: no form input entry from ARCHIVE (only unarchive/delete/info)
            self._message.set(Result(False, None, "Input mode is not available in ARCHIVE view"))
            return

        else:
            self._message.set(Result(False, None, "Input mode is not available in current view"))
            return

        if form_type is None:
            self._message.set(Result(False, None, "No target selected for input"))
            return

        if input_purpose == InputPurpose.EDIT and current_item_id is None:
            self._message.set(Result(False, None, "No item selected for edit"))
            return

        if input_purpose == InputPurpose.ADD:
            if form_type == FormType.PROJECT and context_track_id is None:
                self._message.set(Result(False, None, "No track selected for new project"))
                return
            if form_type == FormType.STRUCTURE_TODO and context_project_id is None:
                self._message.set(Result(False, None, "No project selected for new todo"))
                return

        self._ui_mode = UIMode.INPUT
        self._input_state.set_input_context(
            input_purpose=input_purpose,
            form_type=form_type,
            current_item_id=current_item_id,
            context_track_id=context_track_id,
            context_project_id=context_project_id,
            context_todo_item_id=context_todo_item_id,
            context_now_session_id=context_now_session_id,
        )
        
    def cancel_input(self) -> None:
        """Cancel INPUT mode and return to NORMAL mode."""
        # Special: leaving NOW stage update should still allow recording session description.
        if self._view == View.NOW and self._input_state.form_type == FormType.NOW_STAGE_UPDATE and self._input_state.context_now_session_id is not None:
            session_id = self._input_state.context_now_session_id
            self._ui_mode = UIMode.INPUT
            self._input_state.set_input_context(
                input_purpose=InputPurpose.ADD,
                form_type=FormType.SESSION_DESCRIPTION,
                current_item_id=session_id,
                context_track_id=None,
                context_project_id=self._now_state.current_project_id if self._now_state.current_todo_id is None else None,
                context_todo_item_id=self._now_state.current_todo_id,
                context_now_session_id=session_id,
            )
            self._message.set(Result(True, None, "Add session description"))
            return

        # Special: leaving NOW session description ends the flow.
        if self._view == View.NOW and self._input_state.form_type == FormType.SESSION_DESCRIPTION and self._input_state.context_now_session_id is not None:
            # Session is fully finished (after description capture).
            # If break was armed by a time-up finish, enter BREAK idle 05:00; otherwise reset to WORK idle.
            if self._now_state.maybe_prepare_break_idle():
                self._message.set(Result(True, None, "Session complete. Break ready: press Space to start"))
            else:
                self._now_state.reset_timer()
                self._message.set(Result(True, None, "Session complete"))
        self._input_state.clear_input_context()
        self._ui_mode = UIMode.NORMAL

    def confirm_input(self) -> None:
        """Confirm (submit) current INPUT form and execute corresponding actions."""
        view = self._view
        input_purpose = self._input_state.input_purpose
        form_type = self._input_state.form_type
        created_id = None
        context_track_id = self._input_state.context_track_id
        context_project_id = self._input_state.context_project_id

        # Empty submit behavior (v1): if user didn't enter anything meaningful, treat as cancel (no warning).
        if self._input_state.input_purpose == InputPurpose.ADD:
            title = self._input_state.get_field_str(FormField.TITLE).strip()
            content = self._input_state.get_field_str(FormField.CONTENT).strip()

            # Generic add forms: empty title+content => exit without doing anything.
            if self._input_state.form_type not in (FormType.SESSION_DESCRIPTION, FormType.NOW_STAGE_UPDATE) and not title and not content:
                self.cancel_input()
                return

        result = self._input_state.confirm_input_action()
        self._message.set(result)

        if not result.success:
            return
        if isinstance(result.data, int):
            created_id = result.data

        # Special: after NOW stage update, refresh NOW cache and enter session description.
        if self._view == View.NOW and self._input_state.form_type == FormType.NOW_STAGE_UPDATE and self._input_state.context_now_session_id is not None:
            # Refresh cached todo dict for NOW rendering.
            if self._now_state.current_todo_id is not None and self._now_state.current_project_id is not None and self._now_state.current_track_id is not None:
                self._now_state.set_item(self._now_state.current_track_id, self._now_state.current_project_id, self._now_state.current_todo_id)

            session_id = self._input_state.context_now_session_id
            self._ui_mode = UIMode.INPUT
            self._input_state.set_input_context(
                input_purpose=InputPurpose.ADD,
                form_type=FormType.SESSION_DESCRIPTION,
                current_item_id=session_id,
                context_track_id=None,
                context_project_id=self._now_state.current_project_id if self._now_state.current_todo_id is None else None,
                context_todo_item_id=self._now_state.current_todo_id,
                context_now_session_id=session_id,
            )
            self._message.set(Result(True, None, "Add session description"))
            return

        # Special: after NOW session description, end the finish-session flow.
        if self._view == View.NOW and self._input_state.form_type == FormType.SESSION_DESCRIPTION and self._input_state.context_now_session_id is not None:
            if self._now_state.maybe_prepare_break_idle():
                self._message.set(Result(True, None, "Session complete. Break ready: press Space to start"))
            else:
                self._now_state.reset_timer()
                self._message.set(Result(True, None, "Session complete"))
            self._input_state.clear_input_context()
            self._ui_mode = UIMode.NORMAL
            return

        # Default: Exit INPUT mode
        self._input_state.clear_input_context()
        self._ui_mode = UIMode.NORMAL

        # Refresh view state caches
        if self._view == View.STRUCTURE:
            self._structure_state.load_current_lists()
        elif self._view == View.TIMELINE:
            self._timeline_state.load_timeline_data()
        elif self._view == View.ARCHIVE:
            self._archive_state.load_archive_data()
        elif self._view == View.BOX:
            self._box_state.load_box_lists()

        if input_purpose == InputPurpose.ADD and created_id is not None:
            if view == View.STRUCTURE and form_type is not None:
                if form_type == FormType.TRACK:
                    self._structure_state.focus_track_by_id(created_id)
                elif form_type == FormType.PROJECT:
                    if context_track_id is not None:
                        self._structure_state.focus_track_by_id(context_track_id)
                    self._structure_state.focus_project_by_id(created_id, enter_project_level=True)
                elif form_type == FormType.STRUCTURE_TODO:
                    if context_project_id is not None:
                        self._structure_state.focus_todo_by_id(created_id)
            elif view == View.BOX and form_type is not None:
                if form_type == FormType.BOX_TODO:
                    self._box_state.focus_item_by_id(item_type="todo", item_id=created_id)
                elif form_type == FormType.BOX_IDEA:
                    self._box_state.focus_item_by_id(item_type="idea", item_id=created_id)






    # == Property Getters ========================================================

    @property
    def message(self) -> MessageHolder:
        return self._message
    
    @property
    def view(self) -> View:
        return self._view

    @property
    def from_view(self) -> View | None:
        return self._info_from_view

    @property
    def now_state(self) -> NowState:
        return self._now_state

    @property
    def structure_state(self) -> StructureState:
        return self._structure_state

    @property
    def box_state(self) -> BoxState:
        return self._box_state

    @property
    def info_state(self) -> InfoState:
        return self._info_state

    @property
    def archive_state(self) -> ArchiveState:
        return self._archive_state

    @property
    def timeline_state(self) -> TimelineState:
        return self._timeline_state

    @property
    def ui_mode(self) -> UIMode:
        return self._ui_mode

    @property
    def input_state(self) -> InputState:
        return self._input_state

    @property
    def confirm_action(self) -> ConfirmAction | None:
        return self._confirm_action