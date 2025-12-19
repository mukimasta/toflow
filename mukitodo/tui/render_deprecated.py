# NOTE: This module has been migrated to renderer.py using an OOP approach.
# This file is kept for reference and potential rollback purposes.
# The application now uses the Renderer class from renderer.py.
# See: mukitodo/tui/renderer.py

from typing import TYPE_CHECKING

from mukitodo import actions
from mukitodo.actions import EmptyResult
from mukitodo.tui.state import InputPurpose, StructureLevel, UIMode, View, TimerState

if TYPE_CHECKING:
    from .state import AppState


def _render_now(state: "AppState") -> list:
    """Render NOW view with timer."""
    lines = []
    now_state = state.now_state
    
    # Title
    lines.append(("class:header", "  NOW ACTION\n"))
    lines.append(("class:separator", "  " + "─" * 70 + "\n\n"))
    
    # 1. Todo information section
    if now_state.current_todo_id:
        # Display Track / Project / Todo
        track = actions.get_track(now_state.current_track_id)
        project = actions.get_project(now_state.current_project_id)
        todo = actions.get_todo(now_state.current_todo_id)
        
        if track and project and todo:
            lines.append(("class:dim", f"  Track: {track.name}\n"))
            lines.append(("class:dim", f"  Project: {project.name}\n"))
            marker = "✓" if todo.status == "completed" else "○"
            lines.append(("", f"  Todo: {marker} {todo.content}\n\n"))
        else:
            lines.append(("class:warning", "  Error loading todo information\n\n"))
    else:
        lines.append(("class:warning", "  No todo selected.\n"))
        lines.append(("class:dim", "  Switch to STRUCTURE view and press Enter on a todo.\n\n"))
    
    lines.append(("class:separator", "  " + "─" * 70 + "\n\n"))
    
    # 2. Timer display section (large centered display)
    mins = now_state.remaining_seconds // 60
    secs = now_state.remaining_seconds % 60
    time_str = f"{mins:02d}:{secs:02d}"
    
    # Status icon based on timer state
    if now_state.timer_state == TimerState.RUNNING:
        icon = "▶"
        style = "class:timer_running"
    elif now_state.timer_state == TimerState.PAUSED:
        icon = "⏸"
        style = "class:timer_paused"
    else:
        icon = "⏱"
        style = "class:timer_idle"
    
    # Create large ASCII-style timer display
    lines.append(("", "\n"))
    lines.append(("", "                 "))
    lines.append((style, f"{icon}\n"))
    lines.append(("", "\n"))
    lines.append(("", "            "))
    lines.append((style, f"  {time_str}  \n"))
    lines.append(("", "\n"))
    
    lines.append(("class:separator", "  " + "─" * 70 + "\n\n"))
    
    return lines


def render_main_content(state: "AppState") -> list:
    if state.view == View.NOW:
        return _render_now(state)
    
    # STRUCTURE view
    if state.structure_state.structure_level == StructureLevel.TRACKS:
        return _render_tracks(state)
    elif state.structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
        return _render_tracks_with_projects(state)
    else:  # TODOS
        return _render_items(state)


def _render_tracks(state: "AppState") -> list:
    lines = []
    tracks = actions.list_tracks()
    
    if not tracks:
        lines.append(("class:dim", "  No tracks. Press = to add\n"))
        return lines
    
    lines.append(("class:header", "  Tracks\n\n"))
    
    for idx, track in enumerate(tracks):
        is_selected = idx == state.structure_state.selected_track_idx
        prefix = "▸ " if is_selected else "  "
        style = "class:selected" if is_selected else ""
        lines.append((style, f"{prefix}Track {idx + 1}: {track.name}\n"))
    
    return lines


def _render_tracks_with_projects(state: "AppState") -> list:
    lines = []
    tracks = actions.list_tracks()
    
    if not tracks:
        lines.append(("class:dim", "No tracks. Press : then 'add <name>'\n"))
        return lines
    
    # Determine which tracks to show
    if state.structure_state.show_all_tracks:
        tracks_to_show = tracks
    else:
        # Show only the current track
        if state.structure_state.current_track_id:
            tracks_to_show = [t for t in tracks if t.id == state.structure_state.current_track_id]
        else:
            tracks_to_show = tracks
    
    tracks_with_projects = []
    for track in tracks_to_show:
        projects = actions.list_projects(track.id)
        tracks_with_projects.append((track, projects))
    
    for track_idx_in_all, (track, projects) in enumerate(tracks_with_projects):
        # Find the actual index in the full tracks list
        actual_track_idx = next(i for i, t in enumerate(tracks) if t.id == track.id)
        
        is_track_selected = actual_track_idx == state.structure_state.selected_track_idx
        # Keep track highlighted when selected (either focused on track or projects)
        track_style = "class:selected_track" if is_track_selected else "class:unselected_track"
        
        box_width = 45
        title = f" Track {actual_track_idx + 1}: {track.name} "
        title_len = len(title)
        dash_count = max(1, box_width - 2 - 1 - title_len)
        top_line = "┌─" + title + "─" * dash_count + "┐\n"
        lines.append((track_style, top_line))
        
        if not projects:
            # Highlight "(no projects)" if focus is on projects
            is_empty_focused = is_track_selected and state.structure_state.focus_on_projects
            empty_text = "  (no projects)"
            empty_prefix = "▸ " if is_empty_focused else "  "
            empty_display = f"{empty_prefix}(no projects)"
            padding = max(0, box_width - 2 - len(empty_display))
            empty_style = "class:selected" if is_empty_focused else track_style
            lines.append((empty_style, f"│{empty_display}"))
            lines.append((empty_style if is_empty_focused else "class:dim", " " * padding))
            lines.append((track_style, "│\n"))
        else:
            for proj_idx, project in enumerate(projects):
                is_project_selected = (
                    is_track_selected 
                    and state.structure_state.focus_on_projects 
                    and proj_idx == state.structure_state.selected_project_idx
                )
                proj_prefix = "▸ " if is_project_selected else "  "
                proj_text = f"{proj_prefix}Project {proj_idx + 1}: {project.name}"
                padding = max(0, box_width - 2 - len(proj_text))
                proj_style = "class:selected" if is_project_selected else track_style
                lines.append((proj_style, f"│{proj_text}" + " " * padding + "│\n"))
        
        bottom_line = "└" + "─" * (box_width - 2) + "┘\n"
        lines.append((track_style, bottom_line))
        lines.append(("", "\n"))
    
    return lines


def _render_items(state: "AppState") -> list:
    lines = []
    
    # Get project name by querying actions
    project_name = "Unknown"
    if state.structure_state.current_project_id and state.structure_state.current_track_id:
        projects = actions.list_projects(state.structure_state.current_track_id)
        for project in projects:
            if project.id == state.structure_state.current_project_id:
                project_name = project.name
                break
    
    lines.append(("class:header", f"  Project: {project_name}\n\n"))
    
    if not state.structure_state.current_project_id:
        lines.append(("class:dim", "  No project selected\n"))
        return lines
    
    todos = actions.list_todos(state.structure_state.current_project_id)
    
    if not todos:
        lines.append(("class:dim", "  No items. Press : to add items.\n"))
    else:
        for idx, todo in enumerate(todos):
            is_selected = idx == state.structure_state.selected_todo_idx
            marker = "✓" if todo.status == "completed" else "○"
            prefix = "▸ " if is_selected else "  "
            is_done = todo.status == "completed"
            style = "class:selected" if is_selected else ("class:done" if is_done else "")
            lines.append((style, f"{prefix}Item {idx + 1}: {marker} {todo.content}\n"))
    
    return lines


def render_status_line(state: "AppState") -> list:
    # Show confirmation prompt if in CONFIRM mode
    if state.mode == UIMode.CONFIRM:
        if state.pending_action == "delete":
            message = "Press Backspace again to delete, any other key to cancel"
        elif state.pending_action == "quit":
            message = "Press q again to quit, any other key to cancel"
        elif state.pending_action == "toggle_todo_structure":
            message = "Press Space again to toggle, any other key to cancel"
        elif state.pending_action == "toggle_todo_now":
            message = "Press Enter again to mark toggle, any other key to cancel"
        else:
            message = "Press same key to confirm, any other key to cancel"
        return [
            ("class:warning reverse", " CONFIRM "),
            ("", " "),
            ("class:warning", message)
        ]
    
    # Show last result message if present
    if state.last_result.message:
        style = "class:success" if state.last_result.success else "class:error"
        return [(style, f"  {state.last_result.message}")]
    
    if state.mode == UIMode.COMMAND:
        return [("class:dim", "  [Enter] execute  [Esc/Ctrl+G] exit command mode")]
    
    if state.mode == UIMode.INPUT:
        action = "rename" if state.input_purpose == InputPurpose.RENAME else "add"
        return [("class:dim", f"  [Enter] {action}  [Esc/Ctrl+G] cancel")]
    
    # NOW view
    if state.view == View.NOW:
        now_state = state.now_state
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
    
    # STRUCTURE view
    if state.structure_state.structure_level == StructureLevel.TRACKS:
        return [("class:dim", "  [↑↓] move  [→] select  [Backspace] delete  [=] add  [Tab] NOW  [:] command  [q] quit")]
    
    elif state.structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
        if state.structure_state.focus_on_projects:
            return [("class:dim", "  [↑↓] move  [→] select  [Enter] NOW  [Backspace] delete  [=] add  [←] back  [t] toggle  [Tab] NOW  [:] command  [q] quit")]
        else:
            return [("class:dim", "  [↑↓] move  [→] enter  [Backspace] delete  [=] add  [←] back  [t] toggle  [Tab] NOW  [:] command  [q] quit")]
    
    elif state.structure_state.structure_level == StructureLevel.TODOS:
        return [("class:dim", "  [↑↓] move  [Enter] NOW  [Space] toggle  [Backspace] delete  [=] add  [←] back  [Tab] NOW  [:] command  [q] quit")]
    
    return [("class:dim", "  [↑↓] move  [→] select  [Backspace] delete  [=] add  [←] back  [Tab] NOW  [:] command  [q] quit")]


def render_mode_indicator(state: "AppState") -> list:
    if state.mode == UIMode.COMMAND:
        return [("class:mode", " COMMAND ")]
    if state.mode == UIMode.INPUT:
        if state.input_purpose == InputPurpose.RENAME:
            return [("class:mode", " RENAME ")]
        
        # Add mode
        if state.view == View.NOW:
            return [("class:mode", " NEW ITEM ")]
        elif state.structure_state.structure_level == StructureLevel.TRACKS:
            return [("class:mode", " NEW TRACK ")]
        elif state.structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS:
            return [("class:mode", " NEW PROJECT ")]
        else:
            return [("class:mode", " NEW TODO ")]
    return [("class:mode", " NORMAL ")]


def render_prompt() -> list:
    return [("class:prompt", "> ")]
