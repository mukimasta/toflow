from __future__ import annotations

from enum import Enum

from mukitodo import actions
from mukitodo.actions import Result, EmptyResult
from mukitodo.tui.states.message_holder import MessageHolder


class BoxSubview(Enum):
    TODOS = "todos"
    IDEAS = "ideas"


class BoxState:
    """
    State management for BOX view.

    Responsibilities:
    - Cache box todos / ideas lists for Renderer (Renderer must not call actions).
    - Maintain cursor selection for each subview.
    - Provide selected item context for Info / transfer flows.
    """

    def __init__(self, message_holder: MessageHolder):
        self._message = message_holder

        self._subview: BoxSubview = BoxSubview.TODOS

        self._current_box_todos_list: list[dict] = []
        self._current_box_ideas_list: list[dict] = []

        self._selected_todo_idx: int | None = None
        self._selected_idea_idx: int | None = None

        # Do not auto-load on init; AppState decides when to enter BOX and load.

    # === Data Loading ======================================================

    def load_box_lists(self) -> None:
        """Load todos/ideas from actions and reset selection if needed."""
        todos_result = actions.list_box_todos_dict(include_tui_meta=True)
        self._current_box_todos_list = todos_result.data if (todos_result.success and todos_result.data) else []

        ideas_result = actions.list_idea_items_dict()
        self._current_box_ideas_list = ideas_result.data if (ideas_result.success and ideas_result.data) else []

        # Keep selection stable when possible.
        if self._current_box_todos_list:
            if self._selected_todo_idx is None:
                self._selected_todo_idx = 0
            else:
                self._selected_todo_idx = max(0, min(len(self._current_box_todos_list) - 1, self._selected_todo_idx))
        else:
            self._selected_todo_idx = None

        if self._current_box_ideas_list:
            if self._selected_idea_idx is None:
                self._selected_idea_idx = 0
            else:
                self._selected_idea_idx = max(0, min(len(self._current_box_ideas_list) - 1, self._selected_idea_idx))
        else:
            self._selected_idea_idx = None

    # === Navigation ========================================================

    def move_cursor(self, delta: int) -> None:
        """Move cursor in the current subview."""
        if self._subview == BoxSubview.TODOS:
            if self._selected_todo_idx is None:
                return
            self._selected_todo_idx = max(0, min(len(self._current_box_todos_list) - 1, self._selected_todo_idx + delta))
        else:
            if self._selected_idea_idx is None:
                return
            self._selected_idea_idx = max(0, min(len(self._current_box_ideas_list) - 1, self._selected_idea_idx + delta))

        self._message.set(EmptyResult)

    def set_subview(self, subview: BoxSubview) -> None:
        """Set subview directly (used by AppState when returning from transfer flows)."""
        self._subview = subview
        self._message.set(EmptyResult)

    def focus_item_by_id(self, *, item_type: str, item_id: int) -> None:
        """Focus a box todo/idea by id."""
        self.load_box_lists()
        if item_type == "todo":
            self._subview = BoxSubview.TODOS
            for idx, t in enumerate(self._current_box_todos_list):
                if int(t.get("id")) == int(item_id):
                    self._selected_todo_idx = idx
                    return
        if item_type == "idea":
            self._subview = BoxSubview.IDEAS
            for idx, it in enumerate(self._current_box_ideas_list):
                if int(it.get("id")) == int(item_id):
                    self._selected_idea_idx = idx
                    return

    # === Actions ===========================================================

    def delete_selected_item(self) -> Result:
        """Delete the currently selected todo/idea permanently."""
        item_type, item_id = self.get_selected_item_context()
        if item_type == "none" or item_id is None:
            return Result(False, None, "No item selected")

        if item_type == "todo":
            result = actions.delete_todo(item_id)
        else:
            result = actions.delete_idea_item(item_id)

        if result.success:
            self.load_box_lists()
        self._message.set(result)
        return result

    def archive_selected_item(self) -> Result:
        """Archive the currently selected todo/idea."""
        item_type, item_id = self.get_selected_item_context()
        if item_type == "none" or item_id is None:
            return Result(False, None, "No item selected")

        if item_type == "todo":
            result = actions.archive_todo(item_id)
        else:
            result = actions.archive_idea_item(item_id)

        if result.success:
            self.load_box_lists()
        self._message.set(result)
        return result

    def move_selected_item_order(self, direction: int) -> Result:
        """
        Alt+↑/↓: Move selected item by swapping order_index with neighbor.

        Sorting source of truth is order_index (0..n-1). After move we reload lists
        and re-focus by id to keep cursor on the moved item.
        """
        if direction not in (-1, 1):
            result = Result(False, None, "direction must be -1 or +1")
            self._message.set(result)
            return result

        item_type, item_id = self.get_selected_item_context()
        if item_type == "none" or item_id is None:
            result = Result(False, None, "No item selected")
            self._message.set(result)
            return result

        if item_type == "todo":
            result = actions.move_todo_order(item_id, direction)
        else:
            result = actions.move_idea_order(item_id, direction)

        if result.success:
            self.load_box_lists()
            self.focus_item_by_id(item_type=item_type, item_id=item_id)

        self._message.set(result)
        return result

    # === Selected Context ==================================================

    def get_selected_item_context(self) -> tuple[str, int | None]:
        """Return (item_type, item_id) where item_type is 'todo'|'idea'|'none'."""
        if self._subview == BoxSubview.TODOS:
            if self._selected_todo_idx is None or not self._current_box_todos_list:
                return ("none", None)
            todo = self._current_box_todos_list[self._selected_todo_idx]
            return ("todo", int(todo["id"]))

        if self._selected_idea_idx is None or not self._current_box_ideas_list:
            return ("none", None)
        idea = self._current_box_ideas_list[self._selected_idea_idx]
        return ("idea", int(idea["id"]))

    # === Properties ========================================================

    @property
    def message(self) -> MessageHolder:
        return self._message

    @property
    def subview(self) -> BoxSubview:
        return self._subview

    @property
    def current_box_todos_list(self) -> list[dict]:
        return self._current_box_todos_list

    @property
    def current_box_ideas_list(self) -> list[dict]:
        return self._current_box_ideas_list

    @property
    def selected_todo_idx(self) -> int | None:
        return self._selected_todo_idx

    @property
    def selected_idea_idx(self) -> int | None:
        return self._selected_idea_idx


