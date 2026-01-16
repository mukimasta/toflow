from enum import Enum
import time
from typing import Any
from mukitodo import actions
from mukitodo.actions import Result, EmptyResult
from mukitodo.tui.states.message_holder import MessageHolder




class InfoState:
    """State for INFO view - displays and edits detailed item information."""
    
    def __init__(self, message_holder: MessageHolder):
        self._message = message_holder

        self._selected_field_idx: int = 0 # / cursor
        
        # Context saved when entering INFO view
        self._item_type: str | None = None  # "track", "project", "todo", "idea", "session"

        self._current_track_id: int | None = None
        self._current_project_id: int | None = None
        self._current_todo_id: int | None = None
        self._current_session_id: int | None = None
        self._current_idea_id: int | None = None

        # For Renderer
        self._current_track_name: str | None = None
        self._current_project_name: str | None = None
        self._current_todo_name: str | None = None
        self._field_dict: dict | None = None

        
    def reload_info_panel(self, item_type: str, track_id: int | None, project_id: int | None, todo_id: int | None) -> None:
        """Enter INFO view with saved context."""
        self._selected_field_idx = 0
        self._item_type = item_type # "track", "project", "todo"
        self._current_track_id = track_id
        self._current_project_id = project_id
        self._current_todo_id = todo_id
        self._current_session_id = None
        self._current_idea_id = None

        self._load_field_dict()
        self._load_structure_names()

    def reload_info_panel_for_box(self, item_type: str, item_id: int) -> None:
        """Enter INFO view for box todo or idea."""
        self._selected_field_idx = 0
        self._item_type = item_type  # "todo" or "idea"

        # Clear structure context by default; todo/idea is self-contained.
        self._current_track_id = None
        self._current_project_id = None
        self._current_todo_id = None
        self._current_session_id = None
        self._current_idea_id = None

        if item_type == "todo":
            self._current_todo_id = item_id
        elif item_type == "idea":
            self._current_idea_id = item_id
        else:
            raise ValueError(f"Invalid box item type: {item_type}")

        self._load_field_dict()
        self._load_structure_names()

    def reload_info_panel_for_timeline(self, item_type: str, item_id: int) -> None:
        """Enter INFO view for session from Timeline view."""
        self._selected_field_idx = 0
        self._item_type = item_type  # "session"
        self._current_track_id = None
        self._current_project_id = None
        self._current_todo_id = None
        self._current_idea_id = None

        if item_type == "session":
            self._current_session_id = item_id
        else:
            raise ValueError(f"Invalid item type for timeline: {item_type}")

        self._load_field_dict()
        self._load_structure_names()

    def leave_info_panel(self) -> None:
        """Leave INFO view."""
        self._selected_field_idx = 0
        self._item_type = None
        self._current_track_id = None
        self._current_project_id = None
        self._current_todo_id = None
        self._current_session_id = None
        self._current_idea_id = None
        self._current_track_name = None
        self._current_project_name = None
        self._current_todo_name = None
        self._field_dict = None

    def move_cursor(self, delta: int) -> None:
        """Move cursor between fields with bounds checking."""
        assert self._field_dict is not None
        field_len = len(self._field_dict)
        self._selected_field_idx = max(0, min(field_len - 1, self._selected_field_idx + delta))
        self._message.set(EmptyResult)

    def _load_field_dict(self) -> None:
        """Load field dictionary for current item type."""
        if self._item_type == "track":
            assert self._current_track_id is not None
            result = actions.get_track_dict(self._current_track_id)
        elif self._item_type == "project":
            assert self._current_project_id is not None
            result = actions.get_project_dict(self._current_project_id)
        elif self._item_type == "todo":
            assert self._current_todo_id is not None
            result = actions.get_todo_dict(self._current_todo_id)
        elif self._item_type == "idea":
            assert self._current_idea_id is not None
            result = actions.get_idea_item_dict(self._current_idea_id)
        elif self._item_type == "session":
            assert self._current_session_id is not None
            result = actions.get_session(self._current_session_id)
        else:
            raise ValueError(f"Invalid item type: {self._item_type}")

        if not result.success:
            raise ValueError(f"[Action Error] Failed to get item dictionary: {result.message}")
        self._field_dict = result.data

    def _load_structure_names(self) -> None:
        """Load structure names for breadcrumb display."""
        if self._current_track_id is not None:
            result = actions.get_track_dict(self._current_track_id)
            if not result.success:
                raise ValueError(f"[Action Error] Failed to get track name: {result.message}")
            self._current_track_name = result.data["name"]
        if self._current_project_id is not None:
            result = actions.get_project_dict(self._current_project_id)
            if not result.success:
                raise ValueError(f"[Action Error] Failed to get project name: {result.message}")
            self._current_project_name = result.data["name"]
        if self._current_todo_id is not None:
            result = actions.get_todo_dict(self._current_todo_id)
            if not result.success:
                raise ValueError(f"[Action Error] Failed to get todo name: {result.message}")
            self._current_todo_name = result.data["name"]


    

    @property
    def selected_field_idx(self) -> int:
        return self._selected_field_idx
    
    @property
    def item_type(self) -> str | None:
        return self._item_type
    
    @property
    def current_track_id(self) -> int | None:
        return self._current_track_id
    
    @property
    def current_project_id(self) -> int | None:
        return self._current_project_id
    
    @property
    def current_todo_id(self) -> int | None:
        return self._current_todo_id

    @property
    def current_session_id(self) -> int | None:
        return self._current_session_id

    @property
    def current_track_name(self) -> str | None:
        return self._current_track_name
    
    @property
    def current_project_name(self) -> str | None:
        return self._current_project_name
    
    @property
    def current_todo_name(self) -> str | None:
        return self._current_todo_name
    
    @property
    def field_dict(self) -> dict | None:
        return self._field_dict




'''

TRACK_FIELDS = [
    ("id", False),
    ("name", True),
    ("description", True),
    ("status", False),
    ("archived", False),
    ("created_at_local", False),
    ("archived_at_local", False),
    ("order_index", False),
]

PROJECT_FIELDS = [
    ("id", False),
    ("track_id", False),
    ("name", True),
    ("description", True),
    ("deadline_local", False),
    ("willingness_hint", True),
    ("importance_hint", True),
    ("urgency_hint", True),
    ("status", False),
    ("archived", False),
    ("created_at_local", False),
    ("started_at_local", False),
    ("finished_at_local", False),
    ("archived_at_local", False),
    ("order_index", False),
]

TODO_FIELDS = [
    ("id", False),
    ("project_id", False),
    ("name", True),
    ("description", True),
    ("url", True),
    ("deadline_local", False),
    ("status", False),
    ("archived", False),
    ("created_at_local", False),
    ("completed_at_local", False),
    ("archived_at_local", False),
    ("order_index", False),
]

'''