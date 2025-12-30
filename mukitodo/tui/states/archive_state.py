from mukitodo import actions
from mukitodo.actions import Result, EmptyResult
from mukitodo.tui.states.message_holder import MessageHolder


class ArchiveState:
    """
    Manages Archive View state.

    Data structure:
    - _archive_data: dict - Full hierarchical structure from actions
    - _flat_items: list[tuple] - Flattened list for cursor navigation
      Each tuple: (item_type, item_id, track_id, project_id, todo_id, item_dict)
    - _selected_idx: int | None - Current cursor position in flat_items
    """

    def __init__(self, message_holder: MessageHolder):
        self._message = message_holder

        # Hierarchical data (from actions)
        self._archive_data: dict = {}

        # Flattened data for cursor navigation
        # Each item: (item_type, item_id, track_id, project_id, todo_id, item_dict)
        self._flat_items: list[tuple] = []

        # Cursor position
        self._selected_idx: int | None = None

        # Load initial data
        self.load_archive_data()

    # Data Loading

    def load_archive_data(self) -> None:
        """Load archive tree and flatten it for navigation."""
        result = actions.list_archived_structure()

        if not result.success or not result.data:
            self._archive_data = {"tracks": [], "ideas": []}
            self._flat_items = []
            self._selected_idx = None
            return

        self._archive_data = result.data

        # Flatten tree into navigable list
        flat_list = []

        # Add tracks, projects, and todos
        for track_item in self._archive_data["tracks"]:
            track = track_item["track"]
            track_id = track["id"]

            # Add track to flat list
            flat_list.append((
                "track",
                track_id,
                track_id,
                None,
                None,
                track
            ))

            # Add projects and todos
            for proj_item in track_item["projects"]:
                project = proj_item["project"]
                project_id = project["id"]

                flat_list.append((
                    "project",
                    project_id,
                    track_id,
                    project_id,
                    None,
                    project
                ))

                for todo in proj_item["todos"]:
                    todo_id = todo["id"]
                    flat_list.append((
                        "todo",
                        todo_id,
                        track_id,
                        project_id,
                        todo_id,
                        todo
                    ))

        # Add ideas
        for idea in self._archive_data["ideas"]:
            idea_id = idea["id"]
            flat_list.append((
                "idea",
                idea_id,
                None,
                None,
                None,
                idea
            ))

        self._flat_items = flat_list

        # Set cursor to first item if available
        if self._flat_items and self._selected_idx is None:
            self._selected_idx = 0
        elif self._selected_idx is not None and self._selected_idx >= len(self._flat_items):
            self._selected_idx = max(0, len(self._flat_items) - 1) if self._flat_items else None

    # Cursor Navigation

    def move_cursor(self, delta: int) -> None:
        """Move cursor by delta."""
        if not self._flat_items:
            return

        if self._selected_idx is None:
            self._selected_idx = 0
        else:
            self._selected_idx = max(0, min(
                len(self._flat_items) - 1,
                self._selected_idx + delta
            ))

        self._message.set(EmptyResult)

    # Actions

    def unarchive_selected_item(self) -> None:
        """Unarchive currently selected item."""
        if self._selected_idx is None or not self._flat_items:
            self._message.set(Result(False, None, "No item selected"))
            return

        item_type, item_id, _, _, _, item_dict = self._flat_items[self._selected_idx]

        # Check if item is actually archived
        # Only allow unarchiving of archived items
        if not item_dict.get("archived", False):
            self._message.set(Result(False, None, f"Cannot unarchive unarchived {item_type}. It is only shown because it has archived children."))
            return

        if item_type == "track":
            result = actions.unarchive_track(item_id)
        elif item_type == "project":
            result = actions.unarchive_project(item_id)
        elif item_type == "todo":
            result = actions.unarchive_todo(item_id)
        elif item_type == "idea":
            result = actions.unarchive_idea_item(item_id)
        else:
            result = Result(False, None, f"Unknown item type: {item_type}")

        self.load_archive_data()
        self._message.set(result)

    def delete_selected_item(self) -> None:
        """Permanently delete currently selected item."""
        if self._selected_idx is None or not self._flat_items:
            self._message.set(Result(False, None, "No item selected"))
            return

        item_type, item_id, _, _, _, item_dict = self._flat_items[self._selected_idx]

        # Check if item is actually archived
        # Only allow deletion of archived items to prevent accidental cascade deletion
        if not item_dict.get("archived", False):
            self._message.set(Result(False, None, f"Cannot delete unarchived {item_type}. Archive it first or delete from STRUCTURE view."))
            return

        if item_type == "track":
            result = actions.delete_track(item_id)
        elif item_type == "project":
            result = actions.delete_project(item_id)
        elif item_type == "todo":
            result = actions.delete_todo(item_id)
        elif item_type == "idea":
            result = actions.delete_idea_item(item_id)
        else:
            result = Result(False, None, f"Unknown item type: {item_type}")

        self.load_archive_data()
        self._message.set(result)

    def get_selected_item_context(self) -> tuple[str, int | None, int | None, int | None]:
        """Get context of selected item for INFO view."""
        if self._selected_idx is None or not self._flat_items:
            return ("track", None, None, None)

        item_type, _, track_id, project_id, todo_id, _ = self._flat_items[self._selected_idx]
        return (item_type, track_id, project_id, todo_id)

    # Getters

    @property
    def message(self) -> MessageHolder:
        return self._message

    @property
    def archive_data(self) -> dict:
        """Get hierarchical archive tree for rendering."""
        return self._archive_data

    @property
    def flat_items(self) -> list[tuple]:
        """Get flattened item list."""
        return self._flat_items

    @property
    def selected_idx(self) -> int | None:
        """Get current cursor position."""
        return self._selected_idx
