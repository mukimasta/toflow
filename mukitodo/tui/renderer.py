from typing import TYPE_CHECKING
import unicodedata

from mukitodo import actions
from mukitodo.tui.state import (
    InputPurpose, StructureLevel, UIMode, View, TimerState
)

if TYPE_CHECKING:
    from .state import AppState


class Renderer:
    def __init__(self, state: "AppState"):
        self.state = state

        # == Render Context =================
        self.box_width = 45
        self.separator_width = 70





    # == Render Content =================

    def render_main_content(self) -> list:
        """Render main content based on current view."""
        if self.state.view == View.NOW:
            return self._render_now_main_content()
        
        # STRUCTURE view
        if self.state.structure_state.structure_level == StructureLevel.TRACKS:
            return self._render_tracks_main_content()
        elif self.state.structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
            return self._render_tracks_with_projects_main_content()
        else:  # TODOS
            return self._render_items_main_content()

    def render_status_line(self) -> list:
        """Render status line based on current mode and state."""
        # Show confirmation prompt if in CONFIRM mode
        if self.state.mode == UIMode.CONFIRM:
            if self.state.pending_action == "delete":
                message = "Press Backspace again to delete, any other key to cancel"
            elif self.state.pending_action == "quit":
                message = "Press q again to quit, any other key to cancel"
            elif self.state.pending_action == "toggle_todo_structure":
                message = "Press Space again to toggle, any other key to cancel"
            elif self.state.pending_action == "toggle_todo_now":
                message = "Press Enter again to mark toggle, any other key to cancel"
            else:
                message = "Press same key to confirm, any other key to cancel"
            return [
                ("class:warning reverse", " CONFIRM "),
                ("", " "),
                ("class:warning", message)
            ]
        
        # Show last result message if present
        if self.state.last_result.message:
            style = "class:success" if self.state.last_result.success else "class:error"
            return [(style, f"  {self.state.last_result.message}")]
        
        if self.state.mode == UIMode.COMMAND:
            return [("class:dim", "  [Enter] execute  [Esc/Ctrl+G] exit command mode")]
        
        if self.state.mode == UIMode.INPUT:
            action = "rename" if self.state.input_purpose == InputPurpose.RENAME else "add"
            return [("class:dim", f"  [Enter] {action}  [Esc/Ctrl+G] cancel")]
        
        # Show controls in other situations

        if self.state.view == View.NOW:
            now_state = self.state.now_state
            parts = []
            
            # Timer controls
            if now_state.timer_state == TimerState.IDLE:
                parts.append("[Space] Start")
                parts.append("[+/-] Adjust")
            elif now_state.timer_state == TimerState.RUNNING:
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
        

        if self.state.view == View.STRUCTURE:
            structure_level = self.state.structure_state.structure_level
            parts = []

            parts.extend(["[↑↓] move"])

            if structure_level == StructureLevel.TRACKS:
                parts.extend(["[→] select"])
            elif structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
                parts.extend(["[→] select", "[t] toggle"])
            elif structure_level == StructureLevel.TODOS:
                parts.extend(["[←] back", "[Enter] add to NOW", "[Space] toggle"])

            parts.extend(["[=/+] add", "[Backspace] delete"])
            parts.extend(["[Tab] NOW", "[:] command", "[q] quit"])

            return [("class:dim", "  " + "  ".join(parts))]
        
        # Default fallback
        return [("class:dim", "  [Tab] Switch view  [q] Quit")]

    def render_mode_indicator(self) -> list:
        """Render mode indicator based on current mode."""
        if self.state.mode == UIMode.COMMAND:
            return [("class:mode", " COMMAND ")]
        if self.state.mode == UIMode.INPUT:
            if self.state.input_purpose == InputPurpose.RENAME:
                return [("class:mode", " RENAME ")]
            
            # Add mode
            if self.state.view == View.NOW:
                return [("class:mode", " NEW ITEM ")]
            elif self.state.structure_state.structure_level == StructureLevel.TRACKS:
                return [("class:mode", " NEW TRACK ")]
            elif self.state.structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
                return [("class:mode", " NEW PROJECT ")]
            else:
                return [("class:mode", " NEW TODO ")]
        return [("class:mode", " NORMAL ")]

    def render_prompt(self) -> list:
        """Render command/input prompt."""
        return [("class:prompt", "> ")]



    # == View Renderers =================

    def _render_now_main_content(self) -> list:
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
        """Render TRACKS level view."""
        lines = []
        tracks = actions.list_tracks()
        
        if not tracks:
            lines.append(("class:dim", "  No tracks. Press = to add\n"))
            return lines
        
        lines.append(("class:header", "  Tracks\n\n"))
        
        for idx, track in enumerate(tracks):
            is_selected = idx == self.state.structure_state.selected_track_idx
            prefix = "▸ " if is_selected else "  "
            style = "class:selected" if is_selected else ""
            lines.append((style, f"{prefix}Track {idx + 1}: {track.name}\n"))
        
        return lines

    def _render_tracks_with_projects_main_content(self) -> list:
        """Render TRACKS_WITH_PROJECTS level view."""
        lines = []
        tracks = actions.list_tracks()
        
        if not tracks:
            lines.append(("class:dim", "No tracks. Press : then 'add <name>'\n"))
            return lines
        
        # Determine which tracks to show
        if self.state.structure_state.show_all_tracks:
            tracks_to_show = tracks
        else:
            # Show only the current track
            if self.state.structure_state.current_track_id:
                tracks_to_show = [t for t in tracks if t.id == self.state.structure_state.current_track_id]
            else:
                tracks_to_show = tracks
        
        tracks_with_projects = []
        for track in tracks_to_show:
            projects = actions.list_projects(track.id)
            tracks_with_projects.append((track, projects))
        
        for track_idx_in_all, (track, projects) in enumerate(tracks_with_projects):
            # Find the actual index in the full tracks list
            actual_track_idx = next(i for i, t in enumerate(tracks) if t.id == track.id)
            
            is_track_selected = actual_track_idx == self.state.structure_state.selected_track_idx
            
            # Render single track box
            lines.extend(self._track_with_projects_block(
                track, projects, actual_track_idx, is_track_selected
            ))
        
        return lines

    def _render_items_main_content(self) -> list:
        """Render TODOS level view."""
        lines = []
        
        # Get project name by querying actions
        project_name = "Unknown"
        if self.state.structure_state.current_project_id and self.state.structure_state.current_track_id:
            projects = actions.list_projects(self.state.structure_state.current_track_id)
            for project in projects:
                if project.id == self.state.structure_state.current_project_id:
                    project_name = project.name
                    break
        
        lines.append(("class:header", f"  Project: {project_name}\n\n"))
        
        if not self.state.structure_state.current_project_id:
            lines.append(("class:dim", "  No project selected\n"))
            return lines
        
        todos = actions.list_todos(self.state.structure_state.current_project_id)
        
        if not todos:
            lines.append(("class:dim", "  No items. Press : to add items.\n"))
        else:
            for idx, todo in enumerate(todos):
                is_selected = idx == self.state.structure_state.selected_todo_idx
                marker = "✓" if todo.status == "completed" else "○"
                prefix = "▸ " if is_selected else "  "
                is_done = todo.status == "completed"
                style = "class:selected" if is_selected else ("class:done" if is_done else "")
                lines.append((style, f"{prefix}Item {idx + 1}: {marker} {todo.content}\n"))
        
        return lines



    # == Blocks ================================

    # Blocks for Now View (return content without borders)

    def _now_project_info_content(self) -> list[tuple[str, str]]:
        """Return project info content (no borders)."""
        now_state = self.state.now_state
        
        if now_state.current_todo_id and now_state.current_project_id:
            project = actions.get_project(now_state.current_project_id)
            todo = actions.get_todo(now_state.current_todo_id)
            
            if project and todo:
                marker = "✓" if todo.status == "completed" else "○"
                return [
                    ("", f"{project.name}"),
                    ("", f"{marker} {todo.content}")
                ]
        
        # No todo selected
        return [("class:dim", "--- No Todo Selected ---")]

    def _now_timer_content(self) -> tuple[str, str]:
        """Return timer content (style, text)."""
        now_state = self.state.now_state
        
        # Timer text
        mins = now_state.remaining_seconds // 60
        secs = now_state.remaining_seconds % 60
        time_str = f"{mins:02d}:{secs:02d}"
        
        # Apply style based on state
        if now_state.timer_state == TimerState.RUNNING:
            style = "class:timer_running"
        elif now_state.timer_state == TimerState.PAUSED:
            style = "class:timer_paused"
        else:
            style = "class:timer_idle"
        
        return (style, time_str)

    def _now_status_content(self) -> tuple[str, str]:
        """Return status content with simple symbols (style, text)."""
        now_state = self.state.now_state
        
        if now_state.timer_state == TimerState.RUNNING:
            return ("class:dim", "▶ Running")
        elif now_state.timer_state == TimerState.PAUSED:
            return ("class:dim", "⏸  Paused")
        elif now_state.current_todo_id:
            todo = actions.get_todo(now_state.current_todo_id)
            if todo and todo.status == "completed":
                return ("class:dim", "✓ Finished")
        
        return ("class:dim", "⏱")


    # Blocks for Structure View

    def _tracks_block(self) -> list:
        """Not used - tracks are rendered directly in _render_tracks_main_content."""
        return []

    def _track_with_projects_block(self, track, projects, track_idx, is_track_selected) -> list:
        """Render a single track box with its projects."""
        lines = []
        
        # Keep track highlighted when selected (either focused on track or projects)
        track_style = "class:selected_track" if is_track_selected else "class:unselected_track"
        
        # Build top line with title
        title = f" Track {track_idx + 1}: {track.name} "
        title_display_width = self._display_width(title)  # Fix for Chinese characters
        dash_count = max(1, self.box_width - 2 - 1 - title_display_width)
        top_line = "┌─" + title + "─" * dash_count + "┐\n"
        lines.append((track_style, top_line))
        
        if not projects:
            # Highlight "(no projects)" if focus is on projects
            is_empty_focused = is_track_selected and self.state.structure_state.focus_on_projects
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
                    and self.state.structure_state.focus_on_projects 
                    and proj_idx == self.state.structure_state.selected_project_idx
                )
                proj_prefix = "▸ " if is_project_selected else "  "
                proj_text = f"{proj_prefix}Project {proj_idx + 1}: {project.name}"
                proj_text_width = self._display_width(proj_text)  # Fix for Chinese characters
                padding = max(0, self.box_width - 2 - proj_text_width)
                proj_style = "class:selected" if is_project_selected else track_style
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
    
    