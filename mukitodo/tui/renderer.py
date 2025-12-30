import unicodedata
from datetime import datetime

from mukitodo.tui.states.app_state import AppState, InputPurpose, StructureLevel, UIMode, View
from mukitodo.tui.states.now_state import TimerStateEnum


class Renderer:
    def __init__(self, state: "AppState"):
        self.state = state

        # == Render Context =================
        self.box_width = 45
        self.separator_width = 70





    # == Public Render Methods =================

    def render_now_view_content(self) -> list:
        """Render NOW view content."""
        return self._render_now_view()

    def render_structure_view_content(self) -> list:
        """Render STRUCTURE view content based on current level."""
        if self.state.structure_state.structure_level == StructureLevel.TRACKS:
            return self._render_tracks_main_content()
        elif self.state.structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS_T:
            return self._render_tracks_with_projects_main_content()
        elif self.state.structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            return self._render_tracks_with_projects_main_content()
        else:  # TODOS
            return self._render_items_main_content()

    def render_info_view_content(self) -> list:
        """Render INFO view content."""
        return self._render_info_view()

    def render_archive_view_content(self) -> list:
        """Render ARCHIVE view content."""
        return self._render_archive_view()

    def render_status_line(self) -> list:
        """Render status line based on current mode and state."""
        # Show confirmation prompt if in CONFIRM mode
        if self.state.ui_mode_state.mode == UIMode.CONFIRM:
            confirm_action = self.state.ui_mode_state.confirm_action
            if confirm_action:
                # Build message based on action type
                action_name = confirm_action.name
                action_key = confirm_action.key
                message = f"Press {action_key} again to confirm, any other key to cancel"
            else:
                message = "Press same key to confirm, any other key to cancel"
            return [
                ("class:warning reverse", " CONFIRM "),
                ("", " "),
                ("class:warning", message)
            ]

        # Show last result message if present
        last_result = self.state.message.last_result
        if last_result and last_result.message:
            style = "class:success" if last_result.success else "class:error"
            return [(style, f"  {last_result.message}")]

        if self.state.ui_mode_state.mode == UIMode.COMMAND:
            return [("class:dim", "  [Enter] execute  [Esc/Ctrl+G] exit command mode")]

        if self.state.ui_mode_state.mode == UIMode.INPUT:
            action = "rename" if self.state.ui_mode_state.input_purpose == InputPurpose.STRUCTURE_RENAME_ITEM else "add"
            return [("class:dim", f"  [Enter] {action}  [Esc/Ctrl+G] cancel")]
        
        # Show controls in other situations

        if self.state.view == View.NOW:
            now_state = self.state.now_state
            parts = []
            
            # Timer controls
            if now_state.timer_state == TimerStateEnum.IDLE:
                parts.append("[Space] Start")
                parts.append("[+/-] Adjust")
            elif now_state.timer_state == TimerStateEnum.RUNNING:
                parts.append("[Space] Pause")
                parts.append("[r] Reset")
            else:  # PAUSED
                parts.append("[Space] Resume")
                parts.append("[r] Reset")
            
            # Todo complete
            if now_state.current_todo_id:
                parts.append("[Enter] Mark done")
            
            # Navigation
            parts.append("[Tab] STRUCTURE")
            parts.append("[q] Quit")
            
            return [("class:dim", "  " + "  ".join(parts))]
        

        if self.state.view == View.INFO:
            parts = ["[↑↓] select field", "[r] edit", "[i/Esc] back", "[q] quit"]
            return [("class:dim", "  " + "  ".join(parts))]
        
        if self.state.view == View.STRUCTURE:
            structure_level = self.state.structure_state.structure_level
            parts = []

            parts.extend(["[↑↓] move"])

            if structure_level == StructureLevel.TRACKS:
                parts.extend(["[→] select", "[i] detail"])
            elif structure_level in [StructureLevel.TRACKS_WITH_PROJECTS_T, StructureLevel.TRACKS_WITH_PROJECTS_P]:
                parts.extend(["[→] select", "[i] detail"])
            elif structure_level == StructureLevel.TODOS:
                parts.extend(["[←] back", "[Enter] add to NOW", "[Space] toggle", "[i] detail"])

            parts.extend(["[=/+] add", "[Backspace] delete"])
            parts.extend(["[Tab] NOW", "[:] command", "[q] quit"])

            return [("class:dim", "  " + "  ".join(parts))]

        if self.state.view == View.ARCHIVE:
            parts = ["[↑↓] move", "[u] unarchive", "[Backspace] delete", "[i] detail", "[Esc/A] exit", "[q] quit"]
            return [("class:dim", "  " + "  ".join(parts))]

        # Default fallback
        return [("class:dim", "  [q] Quit")]

    def render_mode_indicator(self) -> list:
        """Render mode indicator based on current mode."""
        if self.state.ui_mode_state.mode == UIMode.COMMAND:
            return [("class:mode", " COMMAND ")]
        if self.state.ui_mode_state.mode == UIMode.INPUT:
            if self.state.ui_mode_state.input_purpose == InputPurpose.STRUCTURE_RENAME_ITEM:
                return [("class:mode", " RENAME ")]
            elif self.state.ui_mode_state.input_purpose == InputPurpose.INFO_EDIT_FIELD:
                return [("class:mode", " EDIT FIELD ")]

            # Add mode
            if self.state.view == View.NOW:
                return [("class:mode", " NEW ITEM ")]
            elif self.state.structure_state.structure_level == StructureLevel.TRACKS:
                return [("class:mode", " NEW TRACK ")]
            elif self.state.structure_state.structure_level in [StructureLevel.TRACKS_WITH_PROJECTS_T, StructureLevel.TRACKS_WITH_PROJECTS_P]:
                return [("class:mode", " NEW PROJECT ")]
            else:
                return [("class:mode", " NEW TODO ")]
        return [("class:mode", " NORMAL ")]

    def render_prompt(self) -> list:
        """Render command/input prompt."""
        return [("class:prompt", "> ")]



    # == View Renderers =================

    def _render_now_view(self) -> list:
        """Render NOW view with centered box layout."""
        lines = []
        box_width = 60
        
        # Top border with embedded title
        lines.extend(self._format_box_top(" NOW ", box_width))
        
        # Empty line (padding)
        lines.extend(self._format_box_empty_line(box_width))
        
        # Project info (get content, center, add borders)
        project_lines = self._now_project_info_content()
        for content in project_lines:
            lines.extend(self._format_box_line(content, box_width, centered=True))
        
        # Empty line separator
        lines.extend(self._format_box_empty_line(box_width))
        lines.extend(self._format_box_empty_line(box_width))
        
        # Timer (get content, center, add borders)
        timer_content = self._now_timer_content()
        lines.extend(self._format_box_line(timer_content, box_width, centered=True))
        
        # Empty line
        lines.extend(self._format_box_empty_line(box_width))
        
        # Status (get content, center, add borders)
        status_content = self._now_status_content()
        lines.extend(self._format_box_line(status_content, box_width, centered=True))
        
        # Empty line (padding)
        lines.extend(self._format_box_empty_line(box_width))
        
        # Bottom border
        lines.extend(self._format_box_bottom(box_width))
        
        return lines

    def _render_structure_main_content(self) -> list:
        """Not used - main_content dispatches directly to specific methods."""
        return []

    def _render_tracks_main_content(self) -> list:
        """Render TRACKS level view. Read from structure_state cached data."""
        lines = []
        tracks = self.state.structure_state.current_tracks_list

        if not tracks:
            lines.append(("class:dim", "  No tracks. Press = to add\n"))
            return lines

        lines.append(("class:header", "  Tracks\n\n"))

        for idx, track in enumerate(tracks):
            is_selected = idx == self.state.structure_state.selected_track_idx
            prefix = "▸ " if is_selected else "  "
            style = self._get_item_style(track, "track", is_selected)
            lines.append((style, f"{prefix}Track {idx + 1}: {track['name']}\n"))

        return lines

    def _render_tracks_with_projects_main_content(self) -> list:
        """Render TRACKS_WITH_PROJECTS level view. Read from structure_state cached data."""
        lines = []
        tracks_with_projects = self.state.structure_state.current_tracks_with_projects_list
        tracks = self.state.structure_state.current_tracks_list

        if not tracks:
            lines.append(("class:dim", "No tracks. Press = to add\n"))
            return lines

        for track_idx, (track, projects) in enumerate(tracks_with_projects):
            is_track_selected = track_idx == self.state.structure_state.selected_track_idx

            # Render single track box
            lines.extend(self._track_with_projects_block(
                track, projects, track_idx, is_track_selected
            ))

        return lines

    def _render_items_main_content(self) -> list:
        """Render TODOS level view. Read from structure_state cached data."""
        lines = []
        todos = self.state.structure_state.current_todos_list

        # Get project name from current_projects_list
        project_name = "Unknown"
        project_id = self.state.structure_state.current_project_id
        if project_id:
            # Find project in current_projects_list (already loaded in structure_state)
            projects = self.state.structure_state.current_projects_list
            for proj in projects:
                if proj["id"] == project_id:
                    project_name = proj["name"]
                    break

        lines.append(("class:header", f"  Project: {project_name}\n\n"))

        if not project_id:
            lines.append(("class:dim", "  No project selected\n"))
            return lines

        if not todos:
            lines.append(("class:dim", "  No items. Press = to add items.\n"))
        else:
            for idx, todo in enumerate(todos):
                is_selected = idx == self.state.structure_state.selected_todo_idx
                prefix = "▸ " if is_selected else "  "

                # Apply status style
                style = self._get_item_style(todo, "todo", is_selected)

                # Keep existing marker logic
                marker = "✓" if todo["status"] == "done" else "○"

                lines.append((style, f"{prefix}Item {idx + 1}: {marker} {todo['name']}\n"))

        return lines
    
    def _render_info_view(self) -> list:
        """Render INFO view for current selected item."""
        lines = []
        
        item_data = self.state.info_state.field_dict
        if not item_data:
            lines.append(("class:error", "  No field data available\n"))
            return lines
        
        for idx, (field_name, value) in enumerate(item_data.items()):
            if value is None:
                display_value = "None"
            elif isinstance(value, datetime):
                display_value = value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                display_value = str(value)
            
            is_selected = idx == self.state.info_state.selected_field_idx
            
            prefix = "▸ " if is_selected else "  "
            line_text = f"{prefix}{field_name}: {display_value}"
            
            style = "class:selected" if is_selected else ""
            lines.append((style, line_text + "\n"))
        
        return lines


    def _render_archive_view(self) -> list:
        """Render ARCHIVE view content."""
        lines = []
        archive_data = self.state.archive_state.archive_data
        flat_items = self.state.archive_state.flat_items
        selected_idx = self.state.archive_state.selected_idx

        if not archive_data or (not archive_data.get("tracks") and not archive_data.get("ideas")):
            lines.append(("class:dim", "  No archived items\n"))
            return lines

        lines.append(("class:header", "  Archive\n\n"))

        # Render Track/Project/Todo tree
        flat_idx = 0
        for track_item in archive_data["tracks"]:
            # Track line
            is_selected = flat_idx == selected_idx
            prefix = "▸ " if is_selected else "  "
            style = self._get_archive_track_style(track_item, is_selected)
            track_status = track_item["track"]["status"]
            # Only show status suffix for unarchived tracks (has archived children case)
            suffix = f" ({track_status})" if not track_item["is_archived"] else ""
            lines.append((style, f"{prefix}Track: {track_item['track']['name']}{suffix}\n"))
            flat_idx += 1

            # Projects under track
            for proj_item in track_item["projects"]:
                is_selected = flat_idx == selected_idx
                prefix = "▸ " if is_selected else "  "
                style = self._get_archive_project_style(proj_item, is_selected)
                project_status = proj_item["project"]["status"]
                # Only show status suffix for unarchived projects (has archived children case)
                suffix = f" ({project_status})" if not proj_item["is_archived"] else ""
                marker = " ✓" if project_status == "finished" else ""
                lines.append((style, f"{prefix}  Project: {proj_item['project']['name']}{marker}{suffix}\n"))
                flat_idx += 1

                # Todos under project
                for todo in proj_item["todos"]:
                    is_selected = flat_idx == selected_idx
                    prefix = "▸ " if is_selected else "  "
                    # Use todo status style instead of archived gray
                    if is_selected:
                        style = "class:selected"
                    else:
                        todo_status = todo["status"]
                        style = f"class:todo.{todo_status}"
                    marker = "✓" if todo["status"] == "done" else "○"
                    lines.append((style, f"{prefix}    {marker} {todo['name']}\n"))
                    flat_idx += 1

            lines.append(("", "\n"))

        # Render Ideas section
        if archive_data["ideas"]:
            lines.append(("class:header", "  Archived Ideas\n\n"))
            for idea in archive_data["ideas"]:
                is_selected = flat_idx == selected_idx
                prefix = "▸ " if is_selected else "  "
                style = "class:selected" if is_selected else "class:idea.archived"
                lines.append((style, f"{prefix}Idea: {idea['name']} (archived)\n"))
                flat_idx += 1

        return lines


    # == Blocks ================================

    # Blocks for Now View (return content without borders)

    def _now_project_info_content(self) -> list[tuple[str, str]]:
        """Return project info content (no borders). Read from now_state cached data."""
        now_state = self.state.now_state

        # Read from cached data in now_state
        project = now_state.current_project_dict
        todo = now_state.current_todo_dict

        if project and todo:
            marker = "✓" if todo["status"] == "done" else "○"
            return [
                ("", f"{project['name']}"),
                ("", f"{marker} {todo['name']}")
            ]
        elif project:
            # Only project selected, no specific todo
            return [("", f"{project['name']}")]

        # No item selected
        return [("class:dim", "--- No Todo Selected ---")]

    def _now_timer_content(self) -> tuple[str, str]:
        """Return timer content (style, text)."""
        now_state = self.state.now_state
        
        # Timer text
        mins = now_state.remaining_seconds // 60
        secs = now_state.remaining_seconds % 60
        time_str = f"{mins:02d}:{secs:02d}"
        
        # Apply style based on state
        if now_state.timer_state == TimerStateEnum.RUNNING:
            style = "class:timer_running"
        elif now_state.timer_state == TimerStateEnum.PAUSED:
            style = "class:timer_paused"
        else:
            style = "class:timer_idle"
        
        return (style, time_str)

    def _now_status_content(self) -> tuple[str, str]:
        """Return status content with simple symbols (style, text). Read from now_state cached data."""
        now_state = self.state.now_state

        if now_state.timer_state == TimerStateEnum.RUNNING:
            return ("class:dim", "▶ Running")
        elif now_state.timer_state == TimerStateEnum.PAUSED:
            return ("class:dim", "⏸  Paused")

        # Check todo status from cached data
        todo = now_state.current_todo_dict
        if todo and todo["status"] == "done":
            return ("class:dim", "✓ Finished")

        return ("class:dim", "⏱")


    # Blocks for Structure View

    def _tracks_block(self) -> list:
        """Not used - tracks are rendered directly in _render_tracks_main_content."""
        return []

    def _track_with_projects_block(self, track, projects, track_idx, is_track_selected) -> list:
        """Render a single track box with its projects."""
        lines = []

        # Apply Track status style (selected_track/unselected_track for compatibility with box borders)
        if is_track_selected:
            track_style = "class:selected_track"
        else:
            # Use status-based style for unselected tracks
            track_style = self._get_item_style(track, "track", False)
            if track_style == "":
                track_style = "class:unselected_track"

        # Build top line with title
        title = f" Track {track_idx + 1}: {track['name']} "
        title_display_width = self._display_width(title)  # Fix for Chinese characters
        dash_count = max(1, self.box_width - 2 - 1 - title_display_width)
        top_line = "┌─" + title + "─" * dash_count + "┐\n"
        lines.append((track_style, top_line))

        if not projects:
            # Highlight "(no projects)" if focus is on projects
            is_empty_focused = is_track_selected and self.state.structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P
            empty_prefix = "▸ " if is_empty_focused else "  "
            empty_display = f"{empty_prefix}(no projects)"
            empty_display_width = self._display_width(empty_display)
            padding = max(0, self.box_width - 2 - empty_display_width)
            empty_style = "class:selected" if is_empty_focused else track_style
            lines.append((empty_style, f"│{empty_display}"))
            lines.append((empty_style if is_empty_focused else "class:dim", " " * padding))
            lines.append((track_style, "│\n"))
        else:
            for proj_idx, project in enumerate(projects):
                is_project_selected = (
                    is_track_selected
                    and self.state.structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P
                    and proj_idx == self.state.structure_state.selected_project_idx
                )

                # Apply Project status style
                proj_style = self._get_item_style(project, "project", is_project_selected)

                proj_prefix = "▸ " if is_project_selected else "  "

                # Add ✓ suffix for finished projects
                status_suffix = " ✓" if project["status"] == "finished" else ""

                proj_text = f"{proj_prefix}Project {proj_idx + 1}: {project['name']}{status_suffix}"
                proj_text_width = self._display_width(proj_text)  # Fix for Chinese characters
                padding = max(0, self.box_width - 2 - proj_text_width)
                lines.append((proj_style, f"│{proj_text}" + " " * padding + "│\n"))

        bottom_line = "└" + "─" * (self.box_width - 2) + "┘\n"
        lines.append((track_style, bottom_line))
        lines.append(("", "\n"))

        return lines

    def _items_block(self) -> list:
        """Not used - items are rendered directly in _render_items_main_content."""
        return []







    # == Helpers ================================

    def _display_width(self, text: str) -> int:
        """Calculate display width of text (CJK characters count as 2, others as 1)."""
        width = 0
        for char in text:
            # Check CJK characters
            char_width = unicodedata.east_asian_width(char)
            if char_width in ('F', 'W'):  # Fullwidth or Wide
                width += 2
            else:
                width += 1
        return width

    def _get_item_style(self, item: dict, item_type: str, is_selected: bool) -> str:
        """
        Get style class for an item based on its status and type.

        Args:
            item: Item dictionary with 'status' field
            item_type: "track", "project", or "todo"
            is_selected: Whether the item is currently selected

        Returns:
            Style class string (e.g., "class:selected", "class:project.sleeping")
        """
        if is_selected:
            return "class:selected"

        status = item.get("status", "active")
        return f"class:{item_type}.{status}"

    def _separator_block(self, width: int = 70) -> list:
        """Render a separator line block."""
        return [("class:separator", "  " + "─" * width + "\n\n")]

    def _format_box_top(self, title: str, width: int) -> list:
        """Format top border with embedded title."""
        title_width = self._display_width(title)
        left_dashes = (width - 2 - title_width) // 2
        right_dashes = width - 2 - title_width - left_dashes
        
        # Return separate styled segments: border (normal) + title (styled) + border (normal)
        return [
            ("", "┌" + "─" * left_dashes),
            ("class:header", title),
            ("", "─" * right_dashes + "┐\n")
        ]

    def _format_box_bottom(self, width: int) -> list:
        """Format bottom border."""
        bottom_line = "└" + "─" * (width - 2) + "┘\n"
        return [("", bottom_line)]

    def _format_box_empty_line(self, width: int) -> list:
        """Format empty line with borders."""
        line = "│" + " " * (width - 2) + "│\n"
        return [("", line)]

    def _format_box_line(self, content: tuple[str, str], width: int, centered: bool = True) -> list:
        """Format content line with borders.
        
        Args:
            content: (style, text) tuple
            width: Box width
            centered: Whether to center the text
        """
        style, text = content
        text_width = self._display_width(text)
        
        if centered:
            left_padding = (width - 2 - text_width) // 2
            right_padding = width - 2 - text_width - left_padding
        else:
            left_padding = 2  # Left align with 2 spaces
            right_padding = width - 2 - text_width - left_padding
        
        return [
            ("", "│" + " " * left_padding),
            (style, text),
            ("", " " * right_padding + "│\n")
        ]

    def _get_archive_track_style(self, track_item: dict, is_selected: bool) -> str:
        """Get style class for archived track."""
        if is_selected:
            return "class:selected"
        return "" if track_item["is_archived"] else "class:dim"

    def _get_archive_project_style(self, proj_item: dict, is_selected: bool) -> str:
        """Get style class for archived project."""
        if is_selected:
            return "class:selected"
        return "" if proj_item["is_archived"] else "class:dim"

