from enum import Enum
from mukitodo import actions
from mukitodo.actions import Result, EmptyResult
from mukitodo.tui.states.message_holder import MessageHolder



class StructureLevel(Enum):
    """Level of the TUI view."""
    TRACKS = "tracks"
    TRACKS_WITH_PROJECTS_T = "tracks_with_projects_tracks"
    TRACKS_WITH_PROJECTS_P = "tracks_with_projects_projects"
    TODOS = "todos"



class StructureState:
    def __init__(self, message_holder: MessageHolder):
        self._message = message_holder
        
        # structure level
        self._structure_level: StructureLevel | None = None

        # current track / project / todo id, real-time update when moving cursor
        self._current_track_id: int | None = None
        self._current_project_id: int | None = None
        self._current_todo_id: int | None = None

        # new implementation: dict list (old implementation is list[int])
        self._current_tracks_list: list[dict] = []
        self._current_tracks_with_projects_list: list[tuple[dict, list[dict]]] = []
        self._current_projects_list: list[dict] = []
        self._current_todos_list: list[dict] = []

        # index of selected track / project / todo
        # NOTE: When the structure view is active, the selected items must have valid [int] values except for there's no track.
        self._selected_track_idx: int | None = None
        self._selected_project_idx: int | None = None
        self._selected_todo_idx: int | None = None


        # initialization
        self.load_current_lists()
        if self._current_tracks_list:
            self._structure_level = StructureLevel.TRACKS_WITH_PROJECTS_T
            self._selected_track_idx = 0
            self.load_current_lists()  # Reload to update _current_track_id based on selected index
        else:
            self._structure_level = StructureLevel.TRACKS
            self.load_current_lists()

    # Navigation State Management

    def move_cursor(self, delta: int) -> None:
        """Move cursor by delta and update _current_*_id."""
        if self._structure_level == StructureLevel.TRACKS:
            if self._selected_track_idx is not None:
                self._selected_track_idx = max(0, min(
                    len(self._current_tracks_list) - 1,
                    self._selected_track_idx + delta
                ))
                self.load_current_lists()

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_T:
            if self._selected_track_idx is not None:
                self._selected_track_idx = max(0, min(
                    len(self._current_tracks_list) - 1,
                    self._selected_track_idx + delta
                ))
                self.load_current_lists()

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            if self._selected_project_idx is not None:
                self._selected_project_idx = max(0, min(
                    len(self._current_projects_list) - 1,
                    self._selected_project_idx + delta
                ))
                self.load_current_lists()

        elif self._structure_level == StructureLevel.TODOS:
            if self._selected_todo_idx is not None:
                self._selected_todo_idx = max(0, min(
                    len(self._current_todos_list) - 1,
                    self._selected_todo_idx + delta
                ))
                self.load_current_lists()

        self._message.set(EmptyResult)

    def select_current(self, enter_todos_level_without_cursor: bool = False) -> None:
        """
        Select the current item (enter track or project).

        enter_todos_level_without_cursor:
        - When entering TODOS from TRACKS_WITH_PROJECTS_P, if True we enter TODOS with no selection
          (cursor None / no highlight). This is used by BOX move confirm UX.
        """
        if self._structure_level == StructureLevel.TRACKS:
            if not self._current_tracks_list:
                self._message.set(Result(False, None, "No tracks available"))
                return
            # Switch level and reload (track_id will be updated by _load_current_lists)
            self._structure_level = StructureLevel.TRACKS_WITH_PROJECTS_T
            self._selected_project_idx = None
            self._selected_todo_idx = None
            self.load_current_lists()
            self._message.set(EmptyResult)

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_T:
            if not self._current_tracks_list:
                self._message.set(Result(False, None, "No tracks available"))
                return
            # Switch level, initialize project selection
            self._structure_level = StructureLevel.TRACKS_WITH_PROJECTS_P
            if self._current_projects_list:
                self._selected_project_idx = 0
            else:
                self._selected_project_idx = None
            self._selected_todo_idx = None
            self.load_current_lists()
            self._message.set(EmptyResult)

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            if not self._current_projects_list:
                self._message.set(Result(False, None, "No projects in this track"))
                return
            # Make sure current_project_id is set before switching level
            if (self._current_projects_list and self._selected_project_idx is not None
                and 0 <= self._selected_project_idx < len(self._current_projects_list)):
                self._current_project_id = self._current_projects_list[self._selected_project_idx]["id"]
            # Switch level, initialize todo selection (need to load todos first)
            self._structure_level = StructureLevel.TODOS
            if enter_todos_level_without_cursor:
                self._selected_todo_idx = None
                self.load_current_lists()
            else:
                # Default: load todos and select first item (if any)
                self.load_current_lists()
                if self._current_todos_list:
                    self._selected_todo_idx = 0
                    self.load_current_lists()  # Reload to update _current_todo_id
                else:
                    self._selected_todo_idx = None
            self._message.set(EmptyResult)

        elif self._structure_level == StructureLevel.TODOS:
            self._message.set(EmptyResult)

        else:
            raise ValueError(f"Invalid structure level: {self._structure_level}")
        
    def go_back(self) -> None:
        """Go back to previous level."""
        if self._structure_level == StructureLevel.TRACKS:
            pass

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_T:
            self._structure_level = StructureLevel.TRACKS
            self._selected_project_idx = None
            self._selected_todo_idx = None
            self.load_current_lists()

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            self._structure_level = StructureLevel.TRACKS_WITH_PROJECTS_T
            self._selected_project_idx = None
            self._selected_todo_idx = None
            self.load_current_lists()

        elif self._structure_level == StructureLevel.TODOS:
            self._structure_level = StructureLevel.TRACKS_WITH_PROJECTS_P
            self._selected_todo_idx = None
            self.load_current_lists()

        else:
            raise ValueError(f"Invalid structure level: {self._structure_level}")

        self._message.set(EmptyResult)

    # === Public helpers for app-level flows (e.g. BOX transfer) =================

    def reset_to_default_view(self) -> None:
        """
        Force STRUCTURE view to TRACKS_WITH_PROJECTS_T level (focus on tracks).
        Used by BOX transfer flows to normalize the entry level.
        """
        self.load_current_lists()
        if not self._current_tracks_list:
            self._structure_level = StructureLevel.TRACKS
            self._selected_track_idx = None
            self._selected_project_idx = None
            self._selected_todo_idx = None
            self.load_current_lists()
            self._message.set(EmptyResult)
            return

        self._structure_level = StructureLevel.TRACKS_WITH_PROJECTS_T
        if self._selected_track_idx is None:
            self._selected_track_idx = 0
        self._selected_project_idx = None
        self._selected_todo_idx = None
        self.load_current_lists()
        self._message.set(EmptyResult)

    # Data Manipulation

    def toggle_selected_item(self) -> None:
        """
        Toggle item status with Space key.
        - TODOS level: Todo done ↔ active (or other → active)
        - TRACKS_WITH_PROJECTS_P level: Project finished ↔ active (or other → active)
        - Other levels: No action
        """
        # Todo toggle (TODOS level)
        if self._structure_level == StructureLevel.TODOS:
            todo = self.current_todo_dict
            if not todo:
                return

            current_status = todo.get("status", "active")

            # Toggle logic: done ↔ active, others → active
            if current_status == "active":
                result = actions.done_todo(self._current_todo_id) # type: ignore
            else:
                result = actions.activate_todo(self._current_todo_id) # type: ignore

            self.load_current_lists()
            self._message.set(result)

        # Project toggle (TRACKS_WITH_PROJECTS_P level)
        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            project = self.current_project_dict
            if not project:
                return

            current_status = project.get("status", "active")

            # Toggle logic: finished ↔ active, others → active
            if current_status == "finished":
                result = actions.activate_project(self._current_project_id) # type: ignore
            elif current_status == "active":
                result = actions.finish_project(self._current_project_id) # type: ignore
            else:
                result = actions.activate_project(self._current_project_id) # type: ignore

            self.load_current_lists()
            self._message.set(result)

    def sleep_selected_item(self) -> None:
        """
        Sleep selected item with 's' key (sleep ↔ active toggle).
        - TRACKS level or TRACKS_WITH_PROJECTS_T: Sleep/activate Track
        - TRACKS_WITH_PROJECTS_P level: Sleep/activate Project
        - TODOS level: Sleep/activate Todo
        """
        # Track sleep
        if self._structure_level in [StructureLevel.TRACKS, StructureLevel.TRACKS_WITH_PROJECTS_T]:
            track = self.current_track_dict
            if not track:
                return

            current_status = track.get("status", "active")

            # Toggle: sleeping ↔ active
            if current_status == "sleeping":
                result = actions.activate_track(self._current_track_id) # type: ignore
            else:
                result = actions.sleep_track(self._current_track_id) # type: ignore

            self.load_current_lists()
            self._message.set(result)

        # Project sleep
        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            project = self.current_project_dict
            if not project:
                return

            current_status = project.get("status", "active")

            # Toggle: sleeping ↔ active
            if current_status == "sleeping":
                result = actions.activate_project(self._current_project_id) # type: ignore
            else:
                result = actions.sleep_project(self._current_project_id) # type: ignore

            self.load_current_lists()
            self._message.set(result)

        # Todo sleep
        elif self._structure_level == StructureLevel.TODOS:
            todo = self.current_todo_dict
            if not todo:
                return

            current_status = todo.get("status", "active")

            # Toggle: sleeping ↔ active
            if current_status == "sleeping":
                result = actions.activate_todo(self._current_todo_id) # type: ignore
            else:
                result = actions.sleep_todo(self._current_todo_id) # type: ignore

            self.load_current_lists()
            self._message.set(result)

    def cancel_selected_item(self) -> None:
        """
        Cancel selected item with 'c' key (cancel ↔ active toggle).
        Only works for Project and Todo (Track cannot be cancelled).
        - TRACKS_WITH_PROJECTS_P level: Cancel/activate Project
        - TODOS level: Cancel/activate Todo
        """
        # Project cancel
        if self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            project = self.current_project_dict
            if not project:
                return

            current_status = project.get("status", "active")

            # Toggle: cancelled ↔ active
            if current_status == "cancelled":
                result = actions.activate_project(self._current_project_id) # type: ignore
            else:
                result = actions.cancel_project(self._current_project_id) # type: ignore

            self.load_current_lists()
            self._message.set(result)

        # Todo cancel
        elif self._structure_level == StructureLevel.TODOS:
            todo = self.current_todo_dict
            if not todo:
                return

            current_status = todo.get("status", "active")

            # Toggle: cancelled ↔ active
            if current_status == "cancelled":
                result = actions.activate_todo(self._current_todo_id) # type: ignore
            else:
                result = actions.cancel_todo(self._current_todo_id) # type: ignore

            self.load_current_lists()
            self._message.set(result)

    def focus_selected_item(self) -> None:
        """
        Focus selected item with 'f' key (focusing ↔ active toggle).
        Only works for Project at TRACKS_WITH_PROJECTS_P level.
        """
        if self._structure_level != StructureLevel.TRACKS_WITH_PROJECTS_P:
            return

        project = self.current_project_dict
        if not project:
            return

        current_status = project.get("status", "active")

        # Toggle: focusing ↔ active
        if current_status == "focusing":
            result = actions.activate_project(self._current_project_id) # type: ignore
        else:
            result = actions.focus_project(self._current_project_id) # type: ignore

        self.load_current_lists()
        self._message.set(result)

    def delete_selected_item(self, ask_confirm: bool = False) -> None:
        """Delete the current item (track, project, or todo)."""

        if ask_confirm:
            self._message.set(Result(False, None, "Delete the current item?"))
            return

        if self._structure_level in [StructureLevel.TRACKS,
                                      StructureLevel.TRACKS_WITH_PROJECTS_T]:
            if not self._current_tracks_list:
                self._message.set(Result(False, None, "No tracks to delete"))
                return
            assert isinstance(self._selected_track_idx, int)
            track = self._current_tracks_list[self._selected_track_idx]
            track_id = track["id"]
            result = actions.delete_track(track_id)
            # Adjust index first, then reload to update _current_track_id
            self.load_current_lists()
            if self._selected_track_idx >= len(self._current_tracks_list):
                self._selected_track_idx = max(0, len(self._current_tracks_list) - 1) if self._current_tracks_list else None
                self.load_current_lists()  # Reload after index adjustment
            self._message.set(result)

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            if not self._current_projects_list:
                self._message.set(Result(False, None, "No projects to delete"))
                return
            assert isinstance(self._selected_project_idx, int)
            project = self._current_projects_list[self._selected_project_idx]
            project_id = project["id"]
            result = actions.delete_project(project_id)
            # Adjust index first, then reload to update _current_project_id
            self.load_current_lists()
            if self._selected_project_idx >= len(self._current_projects_list):
                self._selected_project_idx = max(0, len(self._current_projects_list) - 1) if self._current_projects_list else None
                self.load_current_lists()  # Reload after index adjustment
            self._message.set(result)

        elif self._structure_level == StructureLevel.TODOS:
            if not self._current_todos_list:
                self._message.set(Result(False, None, "No todos to delete"))
                return
            assert isinstance(self._selected_todo_idx, int)
            todo = self._current_todos_list[self._selected_todo_idx]
            todo_id = todo["id"]
            result = actions.delete_todo(todo_id)
            # Adjust index first, then reload to update _current_todo_id
            self.load_current_lists()
            if self._selected_todo_idx >= len(self._current_todos_list):
                self._selected_todo_idx = max(0, len(self._current_todos_list) - 1) if self._current_todos_list else None
                self.load_current_lists()  # Reload after index adjustment
            self._message.set(result)

        else:
            raise ValueError(f"Invalid structure level: {self._structure_level}")

    def archive_selected_item(self) -> None:
        """Archive the currently selected item."""
        if self._structure_level in [StructureLevel.TRACKS, StructureLevel.TRACKS_WITH_PROJECTS_T]:
            # Archive track
            if not self._current_tracks_list:
                self._message.set(Result(False, None, "No tracks to archive"))
                return
            assert isinstance(self._selected_track_idx, int)
            track = self._current_tracks_list[self._selected_track_idx]
            result = actions.archive_track(track["id"])
            self.load_current_lists()
            # Adjust cursor if out of bounds
            if self._current_tracks_list and self._selected_track_idx >= len(self._current_tracks_list):
                self._selected_track_idx = max(0, len(self._current_tracks_list) - 1)
                self.load_current_lists()
            elif not self._current_tracks_list:
                self._selected_track_idx = None
            self._message.set(result)

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            # Archive project
            if not self._current_projects_list:
                self._message.set(Result(False, None, "No projects to archive"))
                return
            assert isinstance(self._selected_project_idx, int)
            project = self._current_projects_list[self._selected_project_idx]
            result = actions.archive_project(project["id"])
            self.load_current_lists()
            # Adjust cursor
            if self._current_projects_list and self._selected_project_idx >= len(self._current_projects_list):
                self._selected_project_idx = max(0, len(self._current_projects_list) - 1)
                self.load_current_lists()
            elif not self._current_projects_list:
                self._selected_project_idx = None
            self._message.set(result)

        elif self._structure_level == StructureLevel.TODOS:
            # Archive todo
            if not self._current_todos_list:
                self._message.set(Result(False, None, "No todos to archive"))
                return
            assert isinstance(self._selected_todo_idx, int)
            todo = self._current_todos_list[self._selected_todo_idx]
            result = actions.archive_todo(todo["id"])
            self.load_current_lists()
            # Adjust cursor
            if self._current_todos_list and self._selected_todo_idx >= len(self._current_todos_list):
                self._selected_todo_idx = max(0, len(self._current_todos_list) - 1)
                self.load_current_lists()
            elif not self._current_todos_list:
                self._selected_todo_idx = None
            self._message.set(result)

    def add_new_item(self, name: str) -> None:
        """Add a new item based on current level."""
        if not name:
            self._message.set(Result(False, None, "Name cannot be empty"))
            return

        if self._structure_level == StructureLevel.TRACKS:
            result = actions.create_track(name)
            self.load_current_lists()
            # Move cursor to the new track and update _current_track_id
            if result.success and self._current_tracks_list:
                self._selected_track_idx = len(self._current_tracks_list) - 1
                self.load_current_lists()  # Reload to update _current_track_id
            self._message.set(result)

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_T:
            # Add a new project to the current track and enter project level
            if self._current_track_id is None:
                self._message.set(Result(False, None, "No track selected"))
                return
            result = actions.create_project(self._current_track_id, name)
            self.load_current_lists()
            # Move to project level and select the new project
            if result.success and self._current_projects_list:
                self._structure_level = StructureLevel.TRACKS_WITH_PROJECTS_P
                self._selected_project_idx = len(self._current_projects_list) - 1
                self.load_current_lists()  # Reload to update _current_project_id
            self._message.set(result)

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            if self._current_track_id is None:
                self._message.set(Result(False, None, "No track selected"))
                return
            result = actions.create_project(self._current_track_id, name)
            self.load_current_lists()
            # Move cursor to the new project and update _current_project_id
            if result.success and self._current_projects_list:
                self._selected_project_idx = len(self._current_projects_list) - 1
                self.load_current_lists()  # Reload to update _current_project_id
            self._message.set(result)

        elif self._structure_level == StructureLevel.TODOS:
            if self._current_project_id is None:
                self._message.set(Result(False, None, "No project selected"))
                return
            result = actions.create_structure_todo(self._current_project_id, name)
            self.load_current_lists()
            # Move cursor to the new todo and update _current_todo_id
            if result.success and self._current_todos_list:
                self._selected_todo_idx = len(self._current_todos_list) - 1
                self.load_current_lists()  # Reload to update _current_todo_id
            self._message.set(result)

        else:
            raise ValueError(f"Invalid structure level: {self._structure_level}")

    def rename_selected_item(self, new_name: str) -> None:
        """Rename current item based on structure level."""
        if not new_name:
            self._message.set(Result(False, None, "Name cannot be empty"))
            return

        if self._structure_level in [StructureLevel.TRACKS,
                                      StructureLevel.TRACKS_WITH_PROJECTS_T]:
            # Rename track
            if not self._current_tracks_list:
                self._message.set(Result(False, None, "No tracks to rename"))
                return
            assert isinstance(self._selected_track_idx, int)
            track = self._current_tracks_list[self._selected_track_idx]
            track_id = track["id"]
            result = actions.rename_track(track_id, new_name)
            self.load_current_lists()
            self._message.set(result)

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            # Rename project
            if not self._current_projects_list:
                self._message.set(Result(False, None, "No projects to rename"))
                return
            assert isinstance(self._selected_project_idx, int)
            project = self._current_projects_list[self._selected_project_idx]
            project_id = project["id"]
            result = actions.rename_project(project_id, new_name)
            self.load_current_lists()
            self._message.set(result)

        elif self._structure_level == StructureLevel.TODOS:
            # Rename todo
            if not self._current_todos_list:
                self._message.set(Result(False, None, "No todos to rename"))
                return
            assert isinstance(self._selected_todo_idx, int)
            todo = self._current_todos_list[self._selected_todo_idx]
            todo_id = todo["id"]
            result = actions.rename_todo(todo_id, new_name)
            self.load_current_lists()
            self._message.set(result)

        else:
            raise ValueError(f"Invalid structure level: {self._structure_level}")
    
    
    # Helper Functions

    def get_selected_item_context(self) -> tuple[str, int | None, int | None, int | None]:
        """Get context of selected item. Return (item_type, track_id, project_id, todo_id)."""
        if self._structure_level in [StructureLevel.TRACKS,
                                      StructureLevel.TRACKS_WITH_PROJECTS_T]:
            item_type = "track"
        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            item_type = "project"
        elif self._structure_level == StructureLevel.TODOS:
            item_type = "todo"
        else:
            raise ValueError(f"Invalid structure level: {self._structure_level}")
        
        return (item_type, self._current_track_id, self._current_project_id, self._current_todo_id)

    def get_current_item_name(self) -> str | None:
        """Get name of current selected item for RENAME INPUT mode."""
        if self._structure_level in [StructureLevel.TRACKS,
                                      StructureLevel.TRACKS_WITH_PROJECTS_T]:
            if not self._current_tracks_list:
                return None
            assert isinstance(self._selected_track_idx, int)
            track = self._current_tracks_list[self._selected_track_idx]
            return track["name"]

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            if not self._current_projects_list:
                return None
            assert isinstance(self._selected_project_idx, int)
            project = self._current_projects_list[self._selected_project_idx]
            return project["name"]

        elif self._structure_level == StructureLevel.TODOS:
            if not self._current_todos_list:
                return None
            assert isinstance(self._selected_todo_idx, int)
            todo = self._current_todos_list[self._selected_todo_idx]
            return todo["name"]

        return None
    
    # def _get_selected_item_id(self) -> int | None:
    #     """Get current selected item ID."""
    #     if self._structure_level in [StructureLevel.TRACKS,
    #                                   StructureLevel.TRACKS_WITH_PROJECTS_T]:
    #         if self._selected_track_idx is not None and self._current_tracks_list:
    #             track = self._current_tracks_list[self._selected_track_idx]
    #             return track["id"]

    #     elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
    #         if self._selected_project_idx is not None and self._current_projects_list:
    #             project = self._current_projects_list[self._selected_project_idx]
    #             return project["id"]

    #     elif self._structure_level == StructureLevel.TODOS:
    #         if self._selected_todo_idx is not None and self._current_todos_list:
    #             todo = self._current_todos_list[self._selected_todo_idx]
    #             return todo["id"]

    #     return None

    def load_current_lists(self) -> None:
        """Load lists based on current level and update _current_*_id based on _selected_*_idx."""

        # All levels need tracks
        result = actions.list_tracks_dict()
        self._current_tracks_list = result.data if (result.success and result.data) else []

        if self._structure_level == StructureLevel.TRACKS:
            # Update track_id, clear lower levels
            if (self._current_tracks_list and self._selected_track_idx is not None
                and 0 <= self._selected_track_idx < len(self._current_tracks_list)):
                self._current_track_id = self._current_tracks_list[self._selected_track_idx]["id"]
            else:
                self._current_track_id = None
            self._current_project_id = None
            self._current_todo_id = None

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_T:
            # Update track_id, dynamically load projects for selected track, clear lower levels
            if (self._current_tracks_list and self._selected_track_idx is not None
                and 0 <= self._selected_track_idx < len(self._current_tracks_list)):
                self._current_track_id = self._current_tracks_list[self._selected_track_idx]["id"]
                assert isinstance(self._current_track_id, int)
                proj_result = actions.list_projects_dict(self._current_track_id, include_tui_meta=True)
                self._current_projects_list = proj_result.data if (proj_result.success and proj_result.data) else []
            else:
                self._current_track_id = None
                self._current_projects_list = []
            self._current_project_id = None
            self._current_todo_id = None

            # Load all tracks with their projects for display
            tracks_with_projects = []
            for track in self._current_tracks_list:
                track_id = track["id"]
                proj_result = actions.list_projects_dict(track_id, include_tui_meta=True)
                project_dicts = proj_result.data if (proj_result.success and proj_result.data) else []
                tracks_with_projects.append((track, project_dicts))
            self._current_tracks_with_projects_list = tracks_with_projects

        elif self._structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            # Load projects based on current track_id, update project_id, clear todo_id
            if self._current_track_id is not None:
                proj_result = actions.list_projects_dict(self._current_track_id, include_tui_meta=True)
                self._current_projects_list = proj_result.data if (proj_result.success and proj_result.data) else []
            else:
                self._current_projects_list = []

            if (self._current_projects_list and self._selected_project_idx is not None
                and 0 <= self._selected_project_idx < len(self._current_projects_list)):
                self._current_project_id = self._current_projects_list[self._selected_project_idx]["id"]
            else:
                self._current_project_id = None
            self._current_todo_id = None

            # Load all tracks with their projects for display
            tracks_with_projects = []
            for track in self._current_tracks_list:
                track_id = track["id"]
                proj_result = actions.list_projects_dict(track_id, include_tui_meta=True)
                project_dicts = proj_result.data if (proj_result.success and proj_result.data) else []
                tracks_with_projects.append((track, project_dicts))
            self._current_tracks_with_projects_list = tracks_with_projects

        elif self._structure_level == StructureLevel.TODOS:
            # Load full hierarchy, update todo_id
            if self._current_track_id is not None:
                proj_result = actions.list_projects_dict(self._current_track_id, include_tui_meta=True)
                self._current_projects_list = proj_result.data if (proj_result.success and proj_result.data) else []
            else:
                self._current_projects_list = []

            if self._current_project_id is not None:
                result = actions.list_structure_todos_dict(self._current_project_id, include_tui_meta=True)
                self._current_todos_list = result.data if (result.success and result.data) else []
            else:
                self._current_todos_list = []

            if (self._current_todos_list and self._selected_todo_idx is not None
                and 0 <= self._selected_todo_idx < len(self._current_todos_list)):
                self._current_todo_id = self._current_todos_list[self._selected_todo_idx]["id"]
            else:
                self._current_todo_id = None
    
    


    # Getter / Properties

    @property
    def message(self) -> MessageHolder:
        return self._message

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
    def current_track_dict(self) -> dict | None:
        """Get current track dict by querying database."""
        if self._current_track_id is None:
            return None
        result = actions.get_track_dict(self._current_track_id)
        return result.data if result.success else None

    @property
    def current_project_dict(self) -> dict | None:
        """Get current project dict by querying database."""
        if self._current_project_id is None:
            return None
        result = actions.get_project_dict(self._current_project_id)
        return result.data if result.success else None

    @property
    def current_todo_dict(self) -> dict | None:
        """Get current todo dict by querying database."""
        if self._current_todo_id is None:
            return None
        result = actions.get_todo_dict(self._current_todo_id)
        return result.data if result.success else None

    @property
    def current_tracks_list(self) -> list[dict]:
        return self._current_tracks_list

    @property
    def current_tracks_with_projects_list(self) -> list[tuple[dict, list[dict]]]:
        return self._current_tracks_with_projects_list

    @property
    def current_projects_list(self) -> list[dict]:
        return self._current_projects_list

    @property
    def current_todos_list(self) -> list[dict]:
        return self._current_todos_list
    
    @property
    def selected_track_idx(self) -> int | None:
        return self._selected_track_idx
    
    @property
    def selected_project_idx(self) -> int | None:
        return self._selected_project_idx
    
    @property
    def selected_todo_idx(self) -> int | None:
        return self._selected_todo_idx