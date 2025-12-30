from dataclasses import dataclass
from enum import Enum
import time
from mukitodo import actions
from mukitodo.actions import Result, EmptyResult
from mukitodo.tui.states.now_state import NowState
from mukitodo.tui.states.structure_state import StructureState, StructureLevel
from mukitodo.tui.states.info_state import InfoState
from mukitodo.tui.states.archive_state import ArchiveState
from mukitodo.tui.states.message_holder import MessageHolder


class View(Enum):
    """View of the TUI."""
    NOW = "now"
    STRUCTURE = "structure"
    INFO = "info"
    ARCHIVE = "archive"





class UIMode(Enum):
    """Mode of the TUI."""
    NORMAL = "normal"
    COMMAND = "command"
    INPUT = "input"
    CONFIRM = "confirm"


class InputPurpose(Enum):
    """Purpose of the input."""
    STRUCTURE_ADD_ITEM = "structure_add_item"
    STRUCTURE_RENAME_ITEM = "structure_rename_item"
    INFO_EDIT_FIELD = "info_edit_field"

class PendingAction(Enum):
    QUIT = ("quit", "q")
    DELETE_STRUCTURE_ITEM = ("delete_structure_item", "backspace")
    ENTER_NOW_WITH_STRUCTURE_ITEM = ("enter_now_with_structure_item", "enter")
    FINISH_SESSION = ("finish_session", "enter")
    ARCHIVE_STRUCTURE_ITEM = ("archive_structure_item", "a")
    UNARCHIVE_ITEM = ("unarchive_item", "u")
    DELETE_ARCHIVE_ITEM = ("delete_archive_item", "backspace")

    @property
    def name(self) -> str:
        return self.value[0]
    @property
    def key(self) -> str:
        return self.value[1]

@dataclass
class UIModeState:
    """State of the UI mode."""
    mode: UIMode
    input_purpose: InputPurpose | None = None
    confirm_action: PendingAction | None = None
    prompt: str | None = None



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

        self._now_state = NowState(self._message)
        self._structure_state = StructureState(self._message)
        self._info_state = InfoState(self._message)
        self._archive_state = ArchiveState(self._message)
        
        # === UI Mode state ===
        self._ui_mode_state: UIModeState = UIModeState(mode=UIMode.NORMAL)


    # == View State Management ==================================================

    def switch_view(self) -> None:
        """Switch between NOW and STRUCTURE views."""
        if self._view == View.NOW:
            self._view = View.STRUCTURE
        elif self._view == View.STRUCTURE:
            self._view = View.NOW

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

    def enter_archive_view(self) -> None:
        """Enter ARCHIVE view from any view."""
        self._view = View.ARCHIVE
        self._archive_state.load_archive_data()

    def exit_archive_view(self) -> None:
        """Exit ARCHIVE view and return to STRUCTURE view."""
        self._view = View.STRUCTURE
        self._structure_state.load_current_lists()

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
        """Finish current NOW session."""
        # TODO: Save session to database in the future
        self._now_state.reset_timer()
        self._message.set(Result(True, None, "Session finished"))




    # == UI State / Mode Management =============================================

    def ask_confirm(self, action: PendingAction) -> None:
        """Enter CONFIRM mode and wait for user confirmation for the given action."""
        self._ui_mode_state.mode = UIMode.CONFIRM
        self._ui_mode_state.confirm_action = action

    def cancel_confirm(self) -> None:
        """Cancel CONFIRM mode and return to NORMAL mode."""
        self._ui_mode_state.mode = UIMode.NORMAL
        self._ui_mode_state.confirm_action = None

    def start_input_and_return_default_value(self, purpose: InputPurpose) -> str | None:
        """Enter INPUT mode for the given purpose and return default value if available."""
        self._ui_mode_state.mode = UIMode.INPUT
        self._ui_mode_state.input_purpose = purpose

        # Return default value based on purpose
        if purpose == InputPurpose.STRUCTURE_ADD_ITEM:
            return None
        elif purpose == InputPurpose.STRUCTURE_RENAME_ITEM:
            return self._structure_state.get_current_item_name()
        elif purpose == InputPurpose.INFO_EDIT_FIELD:
            field_value = self._info_state.get_current_field_value()
            return str(field_value) if field_value is not None else ""

        return None

    def cancel_input(self) -> None:
        """Cancel INPUT mode and return to NORMAL mode."""
        self._ui_mode_state.mode = UIMode.NORMAL
        self._ui_mode_state.input_purpose = None

    def confirm_input(self, value: str) -> None:
        """Confirm input and execute corresponding action based on input_purpose."""
        purpose = self._ui_mode_state.input_purpose

        if purpose == InputPurpose.STRUCTURE_ADD_ITEM:
            self._structure_state.add_new_item(value)
        elif purpose == InputPurpose.STRUCTURE_RENAME_ITEM:
            self._structure_state.rename_selected_item(value)
        elif purpose == InputPurpose.INFO_EDIT_FIELD:
            self._info_state.update_selected_field(value)

        # Return to NORMAL mode
        self._ui_mode_state.mode = UIMode.NORMAL
        self._ui_mode_state.input_purpose = None






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
    def info_state(self) -> InfoState:
        return self._info_state

    @property
    def archive_state(self) -> ArchiveState:
        return self._archive_state

    @property
    def ui_mode_state(self) -> UIModeState:
        return self._ui_mode_state