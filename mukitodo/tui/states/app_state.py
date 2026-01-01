from enum import Enum
from mukitodo import actions
from mukitodo.actions import Result, EmptyResult
from mukitodo.tui.states.message_holder import MessageHolder

from mukitodo.tui.states.now_state import NowState
from mukitodo.tui.states.structure_state import StructureState, StructureLevel
from mukitodo.tui.states.info_state import InfoState
from mukitodo.tui.states.archive_state import ArchiveState
from mukitodo.tui.states.timeline_state import TimelineState
from mukitodo.tui.states.box_state import BoxState, BoxSubview

from mukitodo.tui.states.input_state import FormType, InputPurpose, InputState
from mukitodo.tui.states.input_state import FormField


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
    UNARCHIVE_ITEM = ("unarchive_item", "u")
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
        self._from_view: View | None = None # Track which view we came from when entering INFO view
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

    def switch_view(self) -> None:
        """Switch between NOW and STRUCTURE views."""
        if self._view == View.NOW:
            self._view = View.STRUCTURE
        elif self._view == View.STRUCTURE:
            self._view = View.NOW

    # == Box View ==

    def toggle_box_view(self) -> None:
        """Enter or exit BOX view."""
        if self._view == View.BOX:
            self.exit_box_view()
            return
        self.enter_box_view()

    def enter_box_view(self) -> None:
        """Enter BOX view from any non-INFO view."""
        if self._view == View.INFO:
            # Keep INFO read-only and isolated.
            self._message.set(Result(False, None, "Cannot enter BOX from INFO view"))
            return

        self._box_from_view = self._view
        self._view = View.BOX
        # UX: entering BOX always starts at TODOS.
        self._box_state.set_subview(BoxSubview.TODOS)
        self._box_state.load_box_lists()
        self._message.set(EmptyResult)

    def exit_box_view(self) -> None:
        """Exit BOX view and return to the previous view (NOW/STRUCTURE)."""
        target = self._box_from_view or View.STRUCTURE
        self._box_from_view = None
        self._view = target
        if self._view == View.STRUCTURE:
            self._structure_state.load_current_lists()
        self._message.set(EmptyResult)

    # == Box Transfer (v1) ==

    def has_pending_transfer(self) -> bool:
        """Whether a BOX->STRUCTURE transfer is pending."""
        return self._pending_transfer is not None

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
        self._view = View.STRUCTURE
        self._structure_state.reset_to_default_view()
        self._message.set(Result(True, None, "Move: select a project (→) or enter Todos level (→), then press Enter to confirm"))

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
        self._view = View.STRUCTURE
        self._structure_state.reset_to_default_view()
        self._message.set(Result(True, None, "Promote: select a track, then press Enter to confirm"))

    def cancel_pending_transfer(self) -> None:
        """Cancel a pending BOX transfer and return to BOX."""
        if self._pending_transfer is None:
            return
        return_subview = self._pending_transfer.get("return_box_subview") or BoxSubview.TODOS
        # Exit special no-cursor TODOS confirm state (go back once).
        if self._structure_state.structure_level == StructureLevel.TODOS:
            self._structure_state.go_back()
        self._pending_transfer = None
        self._view = View.BOX
        self._box_state.set_subview(return_subview)
        self._box_state.load_box_lists()
        self._message.set(EmptyResult)

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
            self._view = View.BOX
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
            self._view = View.BOX
            self._box_state.set_subview(BoxSubview.IDEAS)
            self._box_state.load_box_lists()
            return

        self._message.set(Result(False, None, f"Unknown transfer kind: {kind}"))


    def handle_structure_right_for_transfer(self) -> None:
        """
        Handle Right Arrow in STRUCTURE when a BOX transfer is pending.

        - For move_box_todo:
          - In TRACKS_WITH_PROJECTS_P level, Right Arrow enters TODOS level *without* selecting a todo,
            and shows a hint to press Enter to confirm.
          - Otherwise, fall back to normal select_current navigation.
        - For promote_idea: always use normal select_current navigation.
        """
        if self._view != View.STRUCTURE:
            return
        if self._pending_transfer is None:
            self._structure_state.select_current()
            return

        kind = str(self._pending_transfer.get("kind") or "")
        if kind == "move_box_todo" and self._structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            self._structure_state.select_current(enter_todos_level_without_cursor=True)
            # Enter confirm mode immediately when entering TODOS level for move.
            self.ask_confirm(ConfirmAction.CONFIRM_BOX_TRANSFER)
            return

        if kind == "promote_idea":
            # Promote must stay at TRACKS_WITH_PROJECTS_T; do not enter project list.
            if self._structure_state.structure_level != StructureLevel.TRACKS_WITH_PROJECTS_T:
                self._structure_state.reset_to_default_view()
            self.ask_confirm(ConfirmAction.CONFIRM_BOX_TRANSFER)
            return

        self._structure_state.select_current()

    # == Info View ==

    def open_item_info(self) -> None:
        """Open INFO view for currently selected item."""
        if self._view == View.INFO:
            raise ValueError("Already in INFO view")

        # Save current view for returning
        self._from_view = self._view

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
            self._view = View.INFO
            self._info_state.reload_info_panel_for_box(item_type, item_id)
            return
        elif self._view == View.TIMELINE:
            # For Timeline view, get the selected item (session or takeaway)
            item_info = self._timeline_state.get_selected_item_id()
            if item_info is None:
                self._message.set(Result(False, None, "No item selected"))
                return
            item_type, item_id = item_info
            # For session/takeaway, we pass the item_id as the relevant ID
            # Info view needs to handle session and takeaway types
            self._view = View.INFO
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

        self._view = View.INFO
        self._info_state.reload_info_panel(item_type, track_id, project_id, todo_id)

    def return_from_info(self) -> None:
        """Return from INFO view to previous view."""
        if self._from_view is None:
            return

        self._view = self._from_view
        self._from_view = None
        self._info_state.leave_info_panel()
        if self._view == View.STRUCTURE:
            self._structure_state.load_current_lists()
        elif self._view == View.ARCHIVE:
            self._archive_state.load_archive_data()
        elif self._view == View.TIMELINE:
            self._timeline_state.load_timeline_data()

    # == Archive View ==

    def enter_archive_view(self) -> None:
        """Enter ARCHIVE view from any view."""
        self._view = View.ARCHIVE
        self._archive_state.load_archive_data()

    def exit_archive_view(self) -> None:
        """Exit ARCHIVE view and return to STRUCTURE view."""
        self._view = View.STRUCTURE
        self._structure_state.load_current_lists()

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
            self._view = View.BOX
            self._box_state.set_subview(BoxSubview.TODOS)
            self._box_state.load_box_lists()

    # == Timeline View ==

    def enter_timeline_view(self) -> None:
        """Enter TIMELINE view from NOW or STRUCTURE view."""
        self._from_view = self._view
        self._view = View.TIMELINE
        self._timeline_state.load_timeline_data()

    def exit_timeline_view(self) -> None:
        """Exit TIMELINE view and return to previous view."""
        if self._from_view is not None:
            self._view = self._from_view
            self._from_view = None
        else:
            self._view = View.STRUCTURE
        if self._view == View.STRUCTURE:
            self._structure_state.load_current_lists()

    # == Now View ==

    def enter_now_with_structure_item(self) -> None:
        """Enter NOW view with currently selected structure item (project or todo)."""
        item_type, track_id, project_id, todo_id = self._structure_state.get_selected_item_context()

        if item_type not in ["project", "todo"]:
            return

        assert track_id is not None
        assert project_id is not None

        self._now_state.set_item(track_id, project_id, todo_id)
        self._view = View.NOW
        self._message.set(Result(True, None, f"Entered NOW with {item_type}"))

    def finish_session(self) -> None:
        """Finish current NOW session: save to database and enter takeaway input mode."""
        # Save session to database
        result = self._now_state.save_session()
        if not result.success:
            self._message.set(result)
            return

        # Enter INPUT mode for takeaway creation
        session_id = self._now_state.last_saved_session_id
        if session_id is None:
            self._message.set(Result(False, None, "Failed to link takeaways: no session id"))
            return

        # Enter Takeaway Input Mode (allow multiple takeaways; exit with Esc/Ctrl+G or Enter on empty content).
        self._ui_mode = UIMode.INPUT
        self._input_state.set_input_context(
            input_purpose=InputPurpose.ADD,
            form_type=FormType.TAKEAWAY,
            current_item_id=None,
            context_track_id=None,
            context_project_id=self._now_state.current_project_id if self._now_state.current_todo_id is None else None,
            context_todo_item_id=self._now_state.current_todo_id,
            context_now_session_id=session_id,
        )
        self._message.set(Result(True, None, "Session saved. Add takeaways"))

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
            if input_purpose == InputPurpose.ADD:
                form_type = FormType.TAKEAWAY
                parent_session = self._timeline_state.get_parent_session_for_selected()
                if parent_session is None:
                    self._message.set(Result(False, None, "No session to link takeaway to"))
                    return
                context_now_session_id = parent_session.get("id")
                context_project_id = parent_session.get("project_id")
                context_todo_item_id = parent_session.get("todo_item_id")
            else:  # EDIT
                item_info = self._timeline_state.get_selected_item_id()
                if item_info is None:
                    self._message.set(Result(False, None, "No item selected"))
                    return
                item_type, item_id = item_info
                if item_type != "takeaway":
                    self._message.set(Result(False, None, "Only takeaway can be edited in form input"))
                    return
                form_type = FormType.TAKEAWAY
                current_item_id = item_id

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
            if form_type == FormType.TAKEAWAY and (context_project_id is None and context_todo_item_id is None and context_track_id is None):
                # v1: takeaway must be linked to a parent (timeline session provides project/todo); track-level takeaways can be added later.
                self._message.set(Result(False, None, "No parent selected for new takeaway"))
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
        # Special: leaving NOW takeaway capture ends the flow.
        if self._view == View.NOW and self._input_state.form_type == FormType.TAKEAWAY and self._input_state.context_now_session_id is not None:
            self._message.set(Result(True, None, "Session complete"))
        self._input_state.clear_input_context()
        self._ui_mode = UIMode.NORMAL

    def confirm_input(self) -> None:
        """Confirm (submit) current INPUT form and execute corresponding actions."""
        # Empty submit behavior (v1): if user didn't enter anything meaningful, treat as cancel (no warning).
        if self._input_state.input_purpose == InputPurpose.ADD:
            title = self._input_state.get_field_str(FormField.TITLE).strip()
            content = self._input_state.get_field_str(FormField.CONTENT).strip()

            # Generic add forms: empty title+content => exit without doing anything.
            if self._input_state.form_type not in (FormType.TAKEAWAY,) and not title and not content:
                self.cancel_input()
                return

            # Takeaway add (Timeline / NOW capture): empty content => exit without warning.
            if self._input_state.form_type == FormType.TAKEAWAY and not content:
                self.cancel_input()
                return

        # Special: In NOW takeaway capture, Enter on empty content means "done recording".
        if self._view == View.NOW and self._input_state.form_type == FormType.TAKEAWAY and self._input_state.context_now_session_id is not None:
            if not self._input_state.get_field_str(FormField.CONTENT).strip():
                self.cancel_input()
                return

        result = self._input_state.confirm_input_action()
        self._message.set(result)

        if not result.success:
            return

        # Special: Keep INPUT mode for continuous NOW takeaways.
        if self._view == View.NOW and self._input_state.form_type == FormType.TAKEAWAY and self._input_state.context_now_session_id is not None:
            self._input_state.reset_for_next_takeaway()
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






    # == Property Getters ========================================================

    @property
    def message(self) -> MessageHolder:
        return self._message
    
    @property
    def view(self) -> View:
        return self._view

    @property
    def from_view(self) -> View | None:
        return self._from_view

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