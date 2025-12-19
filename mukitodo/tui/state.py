from enum import Enum
import time
from mukitodo import actions
from mukitodo.actions import Result, EmptyResult


class View(Enum):
    """View of the TUI."""
    NOW = "now"
    STRUCTURE = "structure"

class BoxType(Enum):
    """Type of the Box."""
    TODOS = "todos"
    IDEAS = "ideas"

class StructureLevel(Enum):
    """Level of the TUI view."""
    TRACKS = "tracks"
    TRACKS_WITH_PROJECTS = "tracks_with_projects"
    # PROJECTS = "projects"
    TODOS = "todos"

class UIMode(Enum):
    """Mode of the TUI."""
    NORMAL = "normal"
    COMMAND = "command"
    INPUT = "input"
    CONFIRM = "confirm"

class InputPurpose(Enum):
    """Purpose of the input."""
    ADD = "add"
    RENAME = "rename"

class TimerState(Enum):
    """State of the timer."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"





class NowState:
    def __init__(self):
        # current track / project / todo id
        self.current_track_id: int | None = None
        self.current_project_id: int | None = None
        self.current_todo_id: int | None = None
        
        # timer state
        self.timer_state: TimerState = TimerState.IDLE
        self.target_minutes: int = 25
        self.remaining_seconds: int = 25 * 60
        self.start_timestamp: float | None = None
        self.paused_remaining: int | None = None
    
    def set_todo(self, track_id: int, project_id: int, todo_id: int) -> None:
        """Set the current todo for NOW view."""
        self.current_track_id = track_id
        self.current_project_id = project_id
        self.current_todo_id = todo_id
    
    def toggle_timer(self) -> None:
        """Toggle timer between running and paused/idle."""
        if self.timer_state == TimerState.IDLE:
            # Start from idle
            self.timer_state = TimerState.RUNNING
            self.start_timestamp = time.time()
            self.remaining_seconds = self.target_minutes * 60
            self.paused_remaining = None
        elif self.timer_state == TimerState.RUNNING:
            # Pause - immediately update remaining time with rounding
            elapsed = round(time.time() - self.start_timestamp) if self.start_timestamp else 0
            if self.paused_remaining is not None:
                self.remaining_seconds = max(0, self.paused_remaining - elapsed)
            else:
                self.remaining_seconds = max(0, self.target_minutes * 60 - elapsed)
            self.timer_state = TimerState.PAUSED
            self.paused_remaining = self.remaining_seconds
            self.start_timestamp = None
        elif self.timer_state == TimerState.PAUSED:
            # Resume from pause - immediately update display
            self.timer_state = TimerState.RUNNING
            self.start_timestamp = time.time()
            # Set remaining_seconds to paused value for immediate display update
            if self.paused_remaining is not None:
                self.remaining_seconds = self.paused_remaining
    
    def reset_timer(self) -> None:
        """Reset timer to idle state."""
        self.timer_state = TimerState.IDLE
        self.remaining_seconds = self.target_minutes * 60
        self.start_timestamp = None
        self.paused_remaining = None
    
    def adjust_time(self, delta_minutes: int) -> None:
        """Adjust target time by delta minutes."""
        if self.timer_state == TimerState.IDLE:
            new_minutes = max(5, self.target_minutes + delta_minutes)
            self.target_minutes = new_minutes
            self.remaining_seconds = new_minutes * 60
    
    def update_timer(self) -> bool:
        """Update timer state. Returns True if display should be refreshed."""
        if self.timer_state != TimerState.RUNNING or not self.start_timestamp:
            return False
        
        elapsed = round(time.time() - self.start_timestamp)
        
        old_seconds = self.remaining_seconds
        
        if self.paused_remaining is not None:
            # Resuming from pause
            self.remaining_seconds = max(0, self.paused_remaining - elapsed)
        else:
            # Running from start
            self.remaining_seconds = max(0, self.target_minutes * 60 - elapsed)
        
        # Check if timer completed
        if self.remaining_seconds == 0:
            self.timer_state = TimerState.IDLE
            self.start_timestamp = None
            self.paused_remaining = None
            return True  # Always refresh when completed
        
        # Only refresh if seconds changed
        return old_seconds != self.remaining_seconds





class StructureState:
    def __init__(self):
        self._structure_level: StructureLevel | None = None
        
        # current track / project / todo id
        self._current_track_id: int | None = None
        self._current_project_id: int | None = None
        self._current_todo_id: int | None = None

        self._current_tracks_list: list[int] = []
        self._current_tracks_with_projects_list: list[tuple[int, list[int]]] = []
        self._current_projects_list: list[int] = []
        self._current_todos_list: list[int] = []

        # index of selected track / project / todo
        self._selected_track_idx: int | None = None
        self._selected_project_idx: int | None = None
        self._selected_todo_idx: int | None = None

        # display and focus state for TRACKS_WITH_PROJECTS
        self._show_all_tracks: bool = True
        self._focus_on_projects: bool = False

        # initialization
        self._structure_level = StructureLevel.TRACKS_WITH_PROJECTS
        self._selected_track_idx = 0
        self._selected_project_idx = 0
        # self.selected_todo_idx = None
        self._load_current_lists()
    

    # Navigation State Management

    def move_cursor(self, delta: int) -> Result:
        """Move cursor by delta."""
        if self._structure_level == StructureLevel.TRACKS:
            assert isinstance(self._selected_track_idx, int)
            self._selected_track_idx = max(0, min(
                len(self._current_tracks_list) - 1,
                self._selected_track_idx + delta
            ))
        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
            if self._focus_on_projects:
                assert isinstance(self._selected_project_idx, int)
                self._selected_project_idx = max(0, min(
                    len(self._current_projects_list) - 1,
                    self._selected_project_idx + delta
                ))
            else:
                assert isinstance(self._selected_track_idx, int)
                self._selected_track_idx = max(0, min(
                    len(self._current_tracks_list) - 1,
                    self._selected_track_idx + delta
                ))
                # Update current_track_id to sync with selected track
                if self._current_tracks_list:
                    self._current_track_id = self._current_tracks_list[self._selected_track_idx]
                    self._load_current_lists()
        elif self._structure_level == StructureLevel.TODOS:
            assert isinstance(self._selected_todo_idx, int)
            self._selected_todo_idx = max(0, min(
                len(self._current_todos_list) - 1,
                self._selected_todo_idx + delta
            ))
        
        return EmptyResult

    def select_current(self) -> Result:
        """Select the current item (enter track or project)."""
        if self._structure_level == StructureLevel.TRACKS:
            if not self._current_tracks_list:
                return Result("No tracks available", False)
            assert isinstance(self._selected_track_idx, int)
            track_id = self._current_tracks_list[self._selected_track_idx]
            self._structure_level = StructureLevel.TRACKS_WITH_PROJECTS
            # _selected_track_idx is not changed
            self._selected_project_idx = None
            self._selected_todo_idx = None
            self._current_track_id = track_id
            self._current_project_id = None
            self._current_todo_id = None
            self._focus_on_projects = False
            self._load_current_lists()
            return EmptyResult
        
        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
            if self._focus_on_projects:
                if not self._current_projects_list:
                    return Result("No projects in this track", False)
                assert isinstance(self._selected_project_idx, int)
                project_id = self._current_projects_list[self._selected_project_idx]
                self._structure_level = StructureLevel.TODOS
                # _selected_track_idx is not changed
                # _selected_project_idx is not changed
                self._selected_todo_idx = 0
                # _current_track_id is not changed
                self._current_project_id = project_id
                self._current_todo_id = None
                self._load_current_lists()
                return EmptyResult
            else:
                if not self._current_tracks_list:
                    return Result("No tracks available", False)
                assert isinstance(self._selected_track_idx, int)
                track_id = self._current_tracks_list[self._selected_track_idx]
                self._current_track_id = track_id
                self._current_project_id = None
                self._current_todo_id = None
                self._focus_on_projects = True
                self._selected_project_idx = 0
                self._load_current_lists()
                return EmptyResult
        
        elif self._structure_level == StructureLevel.TODOS:
            return Result("Already at bottom level", False)
        
        else:
            raise ValueError(f"Invalid structure level: {self._structure_level}")
        
        
    def go_back(self) -> Result:
        """Go back to previous level."""
        if self._structure_level == StructureLevel.TRACKS:
            return Result("Already at top level", False)
            
        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
            if self._focus_on_projects:
                self._focus_on_projects = False
                return EmptyResult
            else:
                self._structure_level = StructureLevel.TRACKS
                # _selected_track_idx is not changed
                self._selected_project_idx = None
                self._selected_todo_idx = None
                self._current_track_id = None
                self._current_project_id = None
                self._current_todo_id = None
                self._load_current_lists()
                return EmptyResult

        elif self._structure_level == StructureLevel.TODOS:
            self._structure_level = StructureLevel.TRACKS_WITH_PROJECTS
            # _selected_track_idx is not changed
            # _selected_project_idx is not changed
            self._selected_todo_idx = None
            # _current_track_id is not changed
            self._current_project_id = None
            self._current_todo_id = None
            self._focus_on_projects = True
            self._load_current_lists()
            return EmptyResult

        else:
            raise ValueError(f"Invalid structure level: {self._structure_level}")
        
    def toggle_current_todo(self) -> Result:
        """Toggle current todo's done status."""
        if self._structure_level != StructureLevel.TODOS:
            return Result("Not at todo level", False)
        if not self._current_todos_list:
            return Result("No todos in this project", False)
        assert isinstance(self._selected_todo_idx, int)
        todo_id = self._current_todos_list[self._selected_todo_idx]
        result = actions.toggle_todo(todo_id)
        self._load_current_lists()
        return result
    
    def toggle_display_mode(self) -> Result:
        """Toggle display mode between showing all tracks and single track."""
        if self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
            self._show_all_tracks = not self._show_all_tracks
            # When switching to single track mode, ensure current_track_id is synced
            if not self._show_all_tracks and self._current_tracks_list and not self._focus_on_projects:
                assert isinstance(self._selected_track_idx, int)
                self._current_track_id = self._current_tracks_list[self._selected_track_idx]
                self._load_current_lists()
            display_mode = "All tracks" if self._show_all_tracks else "Single track"
            return Result(f"Display: {display_mode}", True)
        return Result("Toggle only available in TRACKS_WITH_PROJECTS", False)
    
    def delete_current(self) -> Result:
        """Delete the current item (track, project, or todo)."""
        if self._structure_level == StructureLevel.TRACKS:
            if not self._current_tracks_list:
                return Result("No tracks to delete", False)
            assert isinstance(self._selected_track_idx, int)
            track_id = self._current_tracks_list[self._selected_track_idx]
            result = actions.delete_track(track_id)
            self._load_current_lists()
            # Adjust cursor if needed
            if self._selected_track_idx >= len(self._current_tracks_list):
                self._selected_track_idx = max(0, len(self._current_tracks_list) - 1)
            return result
        
        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
            if self._focus_on_projects:
                if not self._current_projects_list:
                    return Result("No projects to delete", False)
                assert isinstance(self._selected_project_idx, int)
                project_id = self._current_projects_list[self._selected_project_idx]
                result = actions.delete_project(project_id)
                self._load_current_lists()
                # Adjust cursor if needed
                if self._selected_project_idx >= len(self._current_projects_list):
                    self._selected_project_idx = max(0, len(self._current_projects_list) - 1)
                return result
            else:
                if not self._current_tracks_list:
                    return Result("No tracks to delete", False)
                assert isinstance(self._selected_track_idx, int)
                track_id = self._current_tracks_list[self._selected_track_idx]
                result = actions.delete_track(track_id)
                self._load_current_lists()
                # Adjust cursor if needed
                if self._selected_track_idx >= len(self._current_tracks_list):
                    self._selected_track_idx = max(0, len(self._current_tracks_list) - 1)
                return result
        
        elif self._structure_level == StructureLevel.TODOS:
            if not self._current_todos_list:
                return Result("No todos to delete", False)
            assert isinstance(self._selected_todo_idx, int)
            todo_id = self._current_todos_list[self._selected_todo_idx]
            result = actions.delete_todo(todo_id)
            self._load_current_lists()
            # Adjust cursor if needed
            if self._selected_todo_idx >= len(self._current_todos_list):
                self._selected_todo_idx = max(0, len(self._current_todos_list) - 1)
            return result
        
        else:
            raise ValueError(f"Invalid structure level: {self._structure_level}")
    
    def add_new_item(self, name: str) -> Result:
        """Add a new item based on current level."""
        if not name:
            return Result("Name cannot be empty", False)
        
        if self._structure_level == StructureLevel.TRACKS:
            result = actions.add_track(name)
            self._load_current_lists()
            # Move cursor to the new track
            if result.success and self._current_tracks_list:
                self._selected_track_idx = len(self._current_tracks_list) - 1
            return result
        
        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
            if not self._current_track_id:
                return Result("No track selected", False)
            result = actions.add_project(self._current_track_id, name)
            self._load_current_lists()
            # Move cursor to the new project and switch focus
            if result.success and self._current_projects_list:
                self._selected_project_idx = len(self._current_projects_list) - 1
                self._focus_on_projects = True
            return result
        
        elif self._structure_level == StructureLevel.TODOS:
            if not self._current_project_id:
                return Result("No project selected", False)
            result = actions.add_todo(self._current_project_id, name)
            self._load_current_lists()
            # Move cursor to the new todo
            if result.success and self._current_todos_list:
                self._selected_todo_idx = len(self._current_todos_list) - 1
            return result
    
        else:
            raise ValueError(f"Invalid structure level: {self._structure_level}")
    
    def get_current_item_name(self) -> str | None:
        """Get name of current selected item."""
        if self._structure_level == StructureLevel.TRACKS:
            if not self._current_tracks_list:
                raise ValueError("No tracks available")
            assert isinstance(self._selected_track_idx, int)
            track_id = self._current_tracks_list[self._selected_track_idx]
            track = actions.get_track(track_id)
            if not track:
                raise ValueError(f"Track {track_id} not found")
            return track.name
        
        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
            if self._focus_on_projects:
                if not self._current_projects_list:
                    return None
                assert isinstance(self._selected_project_idx, int)
                project_id = self._current_projects_list[self._selected_project_idx]
                project = actions.get_project(project_id)
                if not project:
                    raise ValueError(f"Project {project_id} not found")
                return project.name
            else:
                if not self._current_tracks_list:
                    raise ValueError("No tracks available")
                assert isinstance(self._selected_track_idx, int)
                track_id = self._current_tracks_list[self._selected_track_idx]
                track = actions.get_track(track_id)
                if not track:
                    raise ValueError(f"Track {track_id} not found")
                return track.name
        
        elif self._structure_level == StructureLevel.TODOS:
            if not self._current_todos_list:
                raise ValueError("No todos available")
            assert isinstance(self._selected_todo_idx, int)
            todo_id = self._current_todos_list[self._selected_todo_idx]
            todo = actions.get_todo(todo_id)
            if not todo:
                raise ValueError(f"Todo {todo_id} not found")
            return todo.content
        
        raise ValueError(f"Invalid structure level: {self._structure_level}")
    
    def rename_current(self, new_name: str) -> Result:
        """Rename current item based on structure level."""
        if not new_name:
            return Result("Name cannot be empty", False)
        
        if self._structure_level == StructureLevel.TRACKS:
            if not self._current_tracks_list:
                return Result("No tracks to rename", False)
            assert isinstance(self._selected_track_idx, int)
            track_id = self._current_tracks_list[self._selected_track_idx]
            result = actions.rename_track(track_id, new_name)
            self._load_current_lists()
            return result
            
        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
            if self._focus_on_projects:
                if not self._current_projects_list:
                    return Result("No projects to rename", False)
                assert isinstance(self._selected_project_idx, int)
                project_id = self._current_projects_list[self._selected_project_idx]
                result = actions.rename_project(project_id, new_name)
                self._load_current_lists()
                return result
            else:
                if not self._current_tracks_list:
                    return Result("No tracks to rename", False)
                assert isinstance(self._selected_track_idx, int)
                track_id = self._current_tracks_list[self._selected_track_idx]
                result = actions.rename_track(track_id, new_name)
                self._load_current_lists()
                return result
        
        elif self._structure_level == StructureLevel.TODOS:
            if not self._current_todos_list:
                return Result("No todos to rename", False)
            assert isinstance(self._selected_todo_idx, int)
            todo_id = self._current_todos_list[self._selected_todo_idx]
            result = actions.rename_todo(todo_id, new_name)
            self._load_current_lists()
            return result
        
        return Result("Invalid structure level", False)
    
    def _load_current_lists(self) -> None:
        """Load the current lists based on the current level, current track, and current project."""
        if self._structure_level == StructureLevel.TRACKS:
            tracks = actions.list_tracks()
            self._current_tracks_list = [t.id for t in tracks]
        
        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
            tracks = actions.list_tracks()
            self._current_tracks_list = [t.id for t in tracks]
            
            # Load tracks with their projects for display
            tracks_with_projects = []
            for track in tracks:
                projects = actions.list_projects(track.id)
                project_ids = [p.id for p in projects]
                tracks_with_projects.append((track.id, project_ids))
            self._current_tracks_with_projects_list = tracks_with_projects
            
            # Load current track's projects if track is selected
            if self._current_track_id:
                projects = actions.list_projects(self._current_track_id)
                self._current_projects_list = [p.id for p in projects]
        
        elif self._structure_level == StructureLevel.TODOS:
            assert isinstance(self._current_project_id, int)
            todos = actions.list_todos(self._current_project_id)
            self._current_todos_list = [t.id for t in todos]

    @property
    def structure_level(self) -> StructureLevel | None:
        return self._structure_level

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
    def selected_track_idx(self) -> int | None:
        return self._selected_track_idx
    
    @property
    def selected_project_idx(self) -> int | None:
        return self._selected_project_idx
    
    @property
    def selected_todo_idx(self) -> int | None:
        return self._selected_todo_idx
    
    @property
    def show_all_tracks(self) -> bool:
        return self._show_all_tracks
    
    @property
    def focus_on_projects(self) -> bool:
        return self._focus_on_projects
    
    @property
    def current_todos_list(self) -> list[int]:
        return self._current_todos_list






class AppState:
    """TUI application state management."""
    
    def __init__(self):
        # view state
        self._view: View = View.NOW
        self._now_state: NowState = NowState()
        self._structure_state: StructureState = StructureState()

        # UI state
        self._mode: UIMode = UIMode.NORMAL
        self._last_result: Result = EmptyResult
        
        # Input mode state
        self._input_purpose: InputPurpose | None = None
        self._rename_target_name: str = ""
        
        # Confirm mode state
        self._pending_action: str | None = None
        self._pending_key: str | None = None


    # View State Management

    @property
    def view(self) -> View:
        return self._view

    def change_view(self, view: View) -> None:
        """Change the view of the TUI."""
        self._view = view
        self._last_result = EmptyResult  # Clear status message when switching views
    

    # UI State / Mode Management

    def execute_command(self, cmd: str) -> Result:
        """Execute a command string."""
        # TODO: Implement this
        return EmptyResult

    @property
    def mode(self) -> UIMode:
        return self._mode
    
    def change_mode(self, mode: UIMode, purpose: InputPurpose | None = None) -> None:
        """Change the mode of the TUI."""
        self._mode = mode
        # Only clear last_result when entering COMMAND or INPUT mode
        # Keep it when returning to NORMAL so user can see operation feedback
        if mode in (UIMode.COMMAND, UIMode.INPUT):
            self._last_result = EmptyResult
        if purpose:
            self._input_purpose = purpose
    
    @property
    def last_result(self) -> Result:
        return self._last_result
    

    # Confirm Mode Management
    
    @property
    def pending_key(self) -> str | None:
        return self._pending_key
    
    @property
    def pending_action(self) -> str | None:
        return self._pending_action
    
    def ask_confirm(self, action: str, key: str) -> None:
        """Enter confirmation mode."""
        self._pending_action = action
        self._pending_key = key
        self._mode = UIMode.CONFIRM
    
    def cancel_confirm(self) -> None:
        """Cancel confirmation and return to NORMAL mode."""
        self._pending_action = None
        self._pending_key = None
        self._mode = UIMode.NORMAL

    # 

    def move_cursor(self, delta: int) -> None:
        """Move cursor by delta."""
        if self._view == View.NOW:
            # self._now_state.move_cursor(delta)
            pass
        elif self._view == View.STRUCTURE:
            result = self._structure_state.move_cursor(delta)
            self._last_result = result
    
    # Structure State Management

    @property
    def structure_state(self) -> StructureState:
        return self._structure_state
    
    @property
    def now_state(self) -> NowState:
        return self._now_state


    def select_current(self) -> None:
        """Select the current item."""
        if self._view == View.STRUCTURE:
            result = self._structure_state.select_current()
            self._last_result = result


    def go_back(self) -> None:
        """Go back to previous level."""
        if self._view == View.STRUCTURE:
            result = self._structure_state.go_back()
            self._last_result = result

    def toggle_current_todo(self) -> None:
        """Toggle current todo's done status."""
        if self._view == View.STRUCTURE:
            result = self._structure_state.toggle_current_todo()
            self._last_result = result

    def delete_current(self) -> None:
        """Delete the current item."""
        if self._view == View.STRUCTURE:
            result = self._structure_state.delete_current()
            self._last_result = result

    def add_new_item(self, name: str) -> None:
        """Add a new item."""
        if self._view == View.STRUCTURE:
            result = self._structure_state.add_new_item(name)
            self._last_result = result
    
    def toggle_display_mode(self) -> None:
        """Toggle display mode in TRACKS_WITH_PROJECTS."""
        if self._view == View.STRUCTURE:
            result = self._structure_state.toggle_display_mode()
            self._last_result = result
    
    # Input Mode Management
    
    @property
    def input_purpose(self) -> InputPurpose | None:
        return self._input_purpose
    
    @property
    def rename_target_name(self) -> str:
        return self._rename_target_name
    
    def start_rename(self) -> str:
        """Start rename mode for current item. Return the current item name."""
        if self._view == View.STRUCTURE:
            current_name = self._structure_state.get_current_item_name()
            if not current_name:
                last_result = Result("No item to rename", False)
                return ""
            self.change_mode(UIMode.INPUT, InputPurpose.RENAME)
            return current_name
        else:
            raise ValueError(f"Invalid view: {self._view}")
    
    def rename_current_item(self, new_name: str) -> None:
        """Rename the current item."""
        if self._view == View.STRUCTURE:
            result = self._structure_state.rename_current(new_name)
            self._last_result = result
        else:
            raise ValueError(f"Invalid view: {self._view}")
    
    # NOW State Management
    
    def enter_now_with_todo(self, track_id: int, project_id: int, todo_id: int) -> None:
        """Switch to NOW view with a selected todo."""
        self._now_state.set_todo(track_id, project_id, todo_id)
        self._view = View.NOW
        self._last_result = EmptyResult
    
    def try_enter_now_from_structure(self) -> None:
        """Try to enter NOW view from current structure position.
        Only works when in TODOS level with a selected todo."""
        
        if self._structure_state.structure_level != StructureLevel.TODOS:
            return
        if not self._structure_state.current_todos_list or self._structure_state.selected_todo_idx is None:
            return
        if not self._structure_state.current_track_id or not self._structure_state.current_project_id:
            return
        
        todo_id = self._structure_state.current_todos_list[self._structure_state.selected_todo_idx]
        self.enter_now_with_todo(self._structure_state.current_track_id, self._structure_state.current_project_id, todo_id)
    
    def toggle_timer(self) -> None:
        """Toggle timer in NOW view."""
        if self._view == View.NOW:
            self._now_state.toggle_timer()
    
    def reset_timer(self) -> None:
        """Reset timer in NOW view."""
        if self._view == View.NOW:
            self._now_state.reset_timer()
    
    def adjust_timer(self, delta: int) -> None:
        """Adjust timer time in NOW view."""
        if self._view == View.NOW:
            self._now_state.adjust_time(delta)
    
    def mark_now_todo_done(self) -> None:
        """Mark the current NOW todo as done."""
        if self._view == View.NOW and self._now_state.current_todo_id:
            result = actions.toggle_todo(self._now_state.current_todo_id)
            self._last_result = result

