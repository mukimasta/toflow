from mukitodo.commands import execute, Result
from mukitodo.services import TrackService, ProjectService, TodoItemService


class AppState:
    """TUI application state management."""
    
    def __init__(self):
        # Navigation
        self.level = "tracks"  # "tracks" | "projects" | "items"
        self.current_track: str | None = None
        self.current_project: str | None = None
        

        # Data
        self._items: list[tuple[str, str]] = []  # (type, name)
        self._tracks_with_projects: list[tuple[str, list[str]]] = []
        self.cursor = 0
        self.selected_track_idx = 0
        self.selected_project_idx = -1
        
        # UI state
        self.mode = "normal"  # "normal" | "command"
        self.last_message = ""
        self.last_success: bool | None = None
        self.confirm_mode: str | None = None  # None | "quit" | "delete"

        # initial load
        self._load_items()

    def _load_items(self):
        """Load items based on current level."""
        self._items = []
        self._tracks_with_projects = []
        
        if self.level == "tracks":
            track_svc = TrackService()
            proj_svc = ProjectService()
            tracks = track_svc.list_all()
            
            for t in tracks:
                projects = [p.name for p in proj_svc.list_by_track(t.name)]
                self._tracks_with_projects.append((t.name, projects))
                self._items.append(("track", t.name))
        
        elif self.level == "projects":
            proj_svc = ProjectService()
            for p in proj_svc.list_by_track(self.current_track):
                self._items.append(("project", p.name))
        
        else:  # items
            item_svc = TodoItemService()
            for item in item_svc.list_by_project(self.current_project):
                status = "done" if item.status == "completed" else "active"
                self._items.append((status, item.content))

        if self.cursor >= len(self._items):
            self.cursor = max(0, len(self._items) - 1)
        
        self._update_selection_indices()

    def refresh(self):
        """Explicitly refresh cached data."""
        self._load_items()

    def _update_selection_indices(self):
        """Update track/project selection indices for tracks view."""
        if self.level != "tracks":
            return
        
        if not self._tracks_with_projects:
            self.selected_track_idx = 0
            self.selected_project_idx = -1
            return
        
        self.selected_track_idx = self.cursor
        self.selected_project_idx = -1

    def get_current_item(self) -> tuple[str, str] | None:
        """Get the currently selected item."""
        if 0 <= self.cursor < len(self._items):
            return self._items[self.cursor]
        return None

    def handle_result(self, result: Result) -> str | None:
        """Handle command result and update state."""
        self.last_message = result.message
        self.last_success = result.success

        if result.action == "quit":
            return "quit"

        if result.action == "select_track":
            self.current_track = result.target
            self.level = "projects"
            self.cursor = 0
        elif result.action == "select_project":
            self.current_project = result.target
            self.level = "items"
            self.cursor = 0
        elif result.action == "back_to_projects":
            self.level = "projects"
            self.current_project = None
            self.cursor = 0
        elif result.action == "back_to_tracks":
            self.level = "tracks"
            self.current_track = None
            self.cursor = 0

        self._load_items()
        return None

    def move_cursor(self, delta: int):
        """Move cursor by delta."""
        if self._items:
            self.cursor = max(0, min(len(self._items) - 1, self.cursor + delta))
            self._update_selection_indices()

    def select_current(self) -> Result | None:
        """Select the current item (enter track or project)."""
        item = self.get_current_item()
        if not item:
            return None

        item_type, name = item
        if item_type in ("track", "project"):
            return execute(f"select {name}", self.level, self.current_track, self.current_project)
        return None

    def toggle_current_item(self) -> Result | None:
        """Toggle current item's done status."""
        if self.level != "items":
            return None
        item = self.get_current_item()
        if not item:
            return None
        status, _ = item
        idx = str(self.cursor + 1)
        if status == "done":
            return execute(f"undo {idx}", self.level, self.current_track, self.current_project)
        else:
            return execute(f"done {idx}", self.level, self.current_track, self.current_project)

    def go_back(self) -> Result:
        """Go back to previous level."""
        return execute("back", self.level, self.current_track, self.current_project)

    def delete_current(self) -> Result | None:
        """Delete the current item."""
        item = self.get_current_item()
        if not item:
            return None
        
        item_type, name = item
        if self.level == "tracks":
            return execute(f"delete {name}", self.level, self.current_track, self.current_project)
        elif self.level == "projects":
            return execute(f"delete {name}", self.level, self.current_track, self.current_project)
        else:  # items
            idx = str(self.cursor + 1)
            return execute(f"delete {idx}", self.level, self.current_track, self.current_project)

    def execute_command(self, cmd: str) -> Result:
        """Execute a command string."""
        return execute(cmd, self.level, self.current_track, self.current_project)

    def is_in_confirm_mode(self) -> bool:
        """Check if in confirmation mode."""
        return self.confirm_mode is not None

    def cancel_confirm(self):
        """Cancel confirmation mode."""
        self.confirm_mode = None

    @property
    def items(self) -> list[tuple[str, str]]:
        """Get current items list."""
        return self._items

    @property
    def tracks_with_projects(self) -> list[tuple[str, list[str]]]:
        """Get tracks with their projects (for tracks view)."""
        return self._tracks_with_projects
