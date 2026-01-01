import unicodedata
from datetime import datetime

from prompt_toolkit.styles import Style

from mukitodo.tui.states.app_state import AppState, StructureLevel, UIMode, View
from mukitodo.tui.states.now_state import TimerStateEnum
from mukitodo.tui.states.input_state import FormField, FormType, InputPurpose


class Renderer:
    def __init__(self, state: "AppState"):
        self.state = state

        # == Render Context =================
        self.box_width = 45
        self.separator_width = 70





    # == Public Render Methods =================

    def build_style(self) -> Style:
        """Build prompt-toolkit Style for the TUI."""
        return Style.from_dict(
            {
                "dim": "ansibrightblack",
                "track": "bold",
                "selected": "reverse",
                "selected_track": "bold ansicyan",
                "unselected_track": "ansibrightblack",
                "header": "bold ansiblue",
                "done": "ansibrightblack",
                "success": "ansigreen",
                "error": "ansired",
                "warning": "ansiyellow",
                "separator": "ansibrightblack",
                "mode": "bg:ansiblue ansiwhite",
                "prompt": "bold",
                "timer_idle": "bold",
                "timer_running": "bold ansigreen",
                "timer_paused": "bold ansiyellow",
                # Deadline styles
                "deadline.past": "ansired",
                # Track status styles
                "track.active": "",
                "track.sleeping": "ansibrightblack",
                # Project status styles
                "project.focusing": "bold",
                "project.active": "",
                "project.sleeping": "ansibrightblack",
                "project.finished": "ansibrightblack",
                "project.cancelled": "ansibrightblack strike",
                # Todo status styles
                "todo.active": "",
                "todo.sleeping": "ansibrightblack",
                "todo.done": "ansibrightblack",
                "todo.cancelled": "ansibrightblack strike",
                # Archive view styles
                "idea.archived": "ansibrightblack",
                "todo.archived": "ansibrightblack",
                # Idea status styles (Box view)
                "idea.active": "",
                "idea.sleeping": "ansibrightblack",
                "idea.deprecated": "ansibrightblack strike",
                "idea.promoted": "ansibrightblack",
                # Cursor visibility (especially important when selected/reverse styles are used)
                "cursor": "bg:ansiwhite ansiblack",
            }
        )

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

    def render_box_view_content(self) -> list:
        """Render BOX view content."""
        return self._render_box_view()

    def render_timeline_view_content(self) -> list:
        """Render TIMELINE view content."""
        return self._render_timeline_view()

    def render_status_line(self) -> list:
        """Render status line based on current mode and state."""
        # Show confirmation prompt if in CONFIRM mode
        if self.state.ui_mode == UIMode.CONFIRM:
            confirm_action = self.state.confirm_action
            if confirm_action:
                # Build message based on action type
                action_name = str(confirm_action.name).replace("_", " ")
                action_key = confirm_action.key
                # Prettify common control-key names for display.
                display_key = {
                    "enter": "Enter",
                    "backspace": "Backspace",
                    "c-m": "Enter",
                    "c-h": "Backspace",
                }.get(action_key, action_key)
                message = f"{action_name}: press {display_key} again to confirm, any other key to cancel"
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

        if self.state.ui_mode == UIMode.COMMAND:
            return [("class:dim", "  [Enter] execute  [Esc/Ctrl+G] exit command mode")]

        if self.state.ui_mode == UIMode.INPUT:
            # Key hints only (Input Mode UI itself is rendered as two-line form panel).
            return [("class:dim", "  [Tab] next/prev  [+/-] adjust  [Space] toggle  [Enter] ok  [Esc/Ctrl+G] cancel")]
        
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
            if now_state.current_todo_id is not None:
                parts.append("[Enter] Mark done")
            
            # Navigation
            parts.append("[Tab] STRUCTURE")
            parts.append("[q] Quit")
            
            return [("class:dim", "  " + "  ".join(parts))]
        

        if self.state.view == View.INFO:
            parts = ["[↑↓] select field", "[i/Esc] back", "[q] quit"]
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

        if self.state.view == View.BOX:
            parts = [
                "[↑↓] move",
                "[[]/[]] switch",
                "[=/+] add",
                "[r] edit",
                "[a] archive",
                "[Backspace] delete",
                "[m] move",
                "[p] promote",
                "[i] detail",
                "[b] back",
                "[q] quit",
            ]
            return [("class:dim", "  " + "  ".join(parts))]

        if self.state.view == View.TIMELINE:
            parts = ["[↑↓] move", "[i] detail", "[=/+] new takeaway", "[r] edit", "[Backspace] delete", "[t/Esc] exit", "[q] quit"]
            return [("class:dim", "  " + "  ".join(parts))]

        # Default fallback
        return [("class:dim", "  [q] Quit")]

    def render_mode_indicator(self) -> list:
        """Render mode indicator based on current mode."""
        if self.state.ui_mode == UIMode.COMMAND:
            return [("class:mode", " COMMAND ")]
        if self.state.ui_mode == UIMode.INPUT:
            input_state = self.state.input_state
            purpose = input_state.input_purpose
            form_type = input_state.form_type
            label = " INPUT "
            if purpose and form_type:
                prefix = "NEW" if purpose == InputPurpose.ADD else "EDIT"
                label = f" {prefix} {form_type.value.upper()} "
            return [("class:mode", label)]
        return [("class:mode", " NORMAL ")]

    def render_prompt(self) -> list:
        """Render command/input prompt."""
        return [("class:prompt", "> ")]

    # == Input Mode Rendering ==================================================

    def render_input_purpose_prompt(self) -> list[tuple[str, str]]:
        """Render the [New X] / [Edit X] prompt shown in Input Mode line 1."""
        input_state = self.state.input_state
        if not input_state.is_active:
            return [("class:dim", "")]

        purpose = input_state.input_purpose
        form_type = input_state.form_type
        if purpose is None or form_type is None:
            return [("class:dim", "")]

        verb = "New" if purpose == InputPurpose.ADD else "Edit"
        label = form_type.value.replace("_", " ").title()
        # Render as a solid mode block (no brackets).
        return [("class:mode", f" {verb} {label} ")]

    def render_input_field_label(self, label: str) -> list[tuple[str, str]]:
        return [("class:dim", label)]

    def render_input_text_value(self, field: FormField) -> list[tuple[str, str]]:
        """Non-active display for a text field (active state uses BufferControl)."""
        input_state = self.state.input_state
        value = input_state.get_field_str(field)
        style = "class:selected" if input_state.current_field == field else ""
        return [(style, value)]

    def render_input_chip(self, field: FormField, label: str) -> list[tuple[str, str]]:
        """Compact '[Label:value]' chip, highlighted when selected."""
        input_state = self.state.input_state
        value = input_state.get_field_display(field)
        style = "class:selected" if input_state.current_field == field else "class:dim"
        return [(style, f"[{label}:{value}]")]

    # == Structure Line Formatting ======================================

    _STATUS_ICON_MAP = {
        "focusing": "📌",
        "active": "○",
        "sleeping": "z",
        "finished": "◉",
        "done": "◉",
        "cancelled": "×",
        "deprecated": "×",
        "promoted": "◉",
    }

    def _get_terminal_width(self, fallback: int = 80) -> int:
        """Best-effort terminal width for alignment. Safe to call without an active app."""
        try:
            from prompt_toolkit.application.current import get_app
            cols = get_app().output.get_size().columns
            return int(cols) if cols and cols > 0 else fallback
        except Exception:
            return fallback

    def _truncate_to_display_width(self, text: str, max_width: int) -> str:
        """Truncate text to fit max display width, appending '…' when truncated."""
        if max_width <= 0:
            return ""
        if self._display_width(text) <= max_width:
            return text

        ellipsis = "…"
        target = max(0, max_width - self._display_width(ellipsis))
        out = []
        used = 0
        for ch in text:
            w = self._display_width(ch)
            if used + w > target:
                break
            out.append(ch)
            used += w
        return "".join(out) + ellipsis

    def _deadline_parts(self, item: dict) -> tuple[str | None, bool]:
        """Return (YYYY-MM-DD, is_past) for deadline_local if present."""
        deadline = item.get("deadline_local")
        if not isinstance(deadline, datetime):
            return (None, False)

        today = datetime.now().astimezone().date()
        ddl_date = deadline.astimezone().date()
        ddl_str = ddl_date.strftime("%Y-%m-%d")
        return (ddl_str, ddl_date < today)

    def _project_hint_icons(self, project: dict) -> list[str]:
        """Project-only hint icons. Display when value is 2-3 (we treat >=2 as visible)."""
        icons: list[str] = []
        if (project.get("willingness_hint") or 0) >= 2:
            icons.append("♥")
        if (project.get("importance_hint") or 0) >= 2:
            icons.append("⭑")
        if (project.get("urgency_hint") or 0) >= 2:
            icons.append("⚡")
        return icons

    def _structure_flags(self, item_type: str, item: dict) -> list[str]:
        flags: list[str] = []
        if item.get("description"):
            flags.append("[≡]")
        if item_type == "todo" and item.get("url"):
            flags.append("[↗]")

        tui = item.get("_tui") or {}
        session_count = int(tui.get("session_count") or 0)
        takeaway_count = int(tui.get("takeaway_count") or 0)
        if item_type in ("project", "todo"):
            if session_count > 0:
                flags.append(f"[⧗{session_count}]")
            if takeaway_count > 0:
                flags.append(f"[✎{takeaway_count}]")
        return flags

    def _structure_line_segments(
        self,
        *,
        item_type: str,
        index_1based: int,
        item: dict,
        is_selected: bool,
        width: int,
    ) -> list[tuple[str, str]]:
        """
        Build a single structure line with right-aligned hints/deadline.
        Returns formatted-text segments (including trailing newline).
        """
        base_style = self._get_item_style(item, item_type, is_selected)

        status = item.get("status", "active")
        icon = self._STATUS_ICON_MAP.get(status, "○")

        left = f"{icon} {item_type.capitalize()} {index_1based}: {item.get('name','')}"
        flags = self._structure_flags(item_type, item)
        if flags:
            left = left + " " + " ".join(flags)

        # Right side: (Project hints) + (deadline)
        right_parts: list[str] = []
        if item_type == "project":
            right_parts.extend(self._project_hint_icons(item))

        ddl_str, ddl_is_past = self._deadline_parts(item)
        if ddl_str:
            right_parts.append(ddl_str)

        # If space is tight, prefer keeping the deadline (last) and dropping hint icons first.
        right_text = " ".join(right_parts)
        left_width = self._display_width(left)
        right_width = self._display_width(right_text)

        if right_text and (left_width + 2 + right_width) > width and len(right_parts) > 1:
            # Keep only the last part (deadline) if present.
            right_parts = right_parts[-1:]
            right_text = " ".join(right_parts)
            right_width = self._display_width(right_text)

        # If left alone is too long, truncate left to fit.
        if left_width > width:
            left = self._truncate_to_display_width(left, width)
            left_width = self._display_width(left)

        if right_text and (left_width + 2 + right_width) <= width:
            pad_spaces = width - left_width - right_width
            pad = " " * pad_spaces
            segments: list[tuple[str, str]] = [(base_style, left), (base_style, pad)]

            if ddl_str and right_text.endswith(ddl_str) and ddl_is_past:
                hints_text = right_text[: -len(ddl_str)].rstrip()
                if hints_text:
                    segments.append((base_style, hints_text + " "))
                segments.append(("class:deadline.past", ddl_str))
            else:
                segments.append((base_style, right_text))

            segments.append((base_style, "\n"))
            return segments

        # Fallback: if it doesn't fit, drop right_text.
        text = left
        if self._display_width(text) > width:
            text = self._truncate_to_display_width(text, width)
        return [(base_style, text + "\n")]



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
        if project_id is not None:
            # Find project in current_projects_list (already loaded in structure_state)
            projects = self.state.structure_state.current_projects_list
            for proj in projects:
                if proj["id"] == project_id:
                    project_name = proj["name"]
                    break

        lines.append(("class:header", f"  Project: {project_name}\n\n"))

        if project_id is None:
            lines.append(("class:dim", "  No project selected\n"))
            return lines

        if not todos:
            lines.append(("class:dim", "  No items. Press = to add items.\n"))
        else:
            for idx, todo in enumerate(todos):
                is_selected = idx == self.state.structure_state.selected_todo_idx
                indent = "  "
                width = max(40, self._get_terminal_width() - 2)
                segs = self._structure_line_segments(
                    item_type="todo",
                    index_1based=idx + 1,
                    item=todo,
                    is_selected=is_selected,
                    width=max(20, width - self._display_width(indent)),
                )
                lines.append(("", indent))
                lines.extend(segs)

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
        if archive_data.get("ideas"):
            lines.append(("class:header", "  Archived Ideas\n\n"))
            for idea in archive_data.get("ideas", []):
                is_selected = flat_idx == selected_idx
                prefix = "▸ " if is_selected else "  "
                style = "class:selected" if is_selected else "class:idea.archived"
                lines.append((style, f"{prefix}Idea: {idea['name']} (archived)\n"))
                flat_idx += 1

            lines.append(("", "\n"))

        # Render Box Todos section (archived todos with project_id is NULL)
        if archive_data.get("box_todos"):
            lines.append(("class:header", "  Archived Box Todos\n\n"))
            for todo in archive_data.get("box_todos", []):
                is_selected = flat_idx == selected_idx
                prefix = "▸ " if is_selected else "  "
                if is_selected:
                    style = "class:selected"
                else:
                    todo_status = todo.get("status", "active")
                    style = f"class:todo.{todo_status}"
                marker = "✓" if todo.get("status") == "done" else "○"
                lines.append((style, f"{prefix}{marker} Todo: {todo.get('name','')}\n"))
                flat_idx += 1

        return lines

    def _render_box_view(self) -> list:
        """Render BOX view content (Todos/Ideas subviews)."""
        lines: list[tuple[str, str]] = []

        box_state = self.state.box_state
        subview = box_state.subview

        lines.append(("class:header", "  BOX\n\n"))

        hint = f"  Subview: {subview.value.upper()}   ([ / ] switch)\n\n"
        lines.append(("class:dim", hint))

        width = max(40, self._get_terminal_width() - 2)

        if subview.value == "todos":
            items = box_state.current_box_todos_list
            selected_idx = box_state.selected_todo_idx
            item_type = "todo"
        else:
            items = box_state.current_box_ideas_list
            selected_idx = box_state.selected_idea_idx
            item_type = "idea"

        if not items:
            empty_label = "No box todos. Press = to add\n" if item_type == "todo" else "No ideas. Press = to add\n"
            lines.append(("class:dim", f"  {empty_label}"))
            return lines

        for idx, item in enumerate(items):
            is_selected = (selected_idx == idx)
            segs = self._structure_line_segments(
                item_type=item_type,
                index_1based=idx + 1,
                item=item,
                is_selected=is_selected,
                width=width,
            )
            lines.append(("", "  "))
            lines.extend(segs)

        return lines

    def _render_timeline_view(self) -> list:
        """Render TIMELINE view content with tree-style layout."""
        lines = []
        timeline_state = self.state.timeline_state
        flat_rows = timeline_state.flat_rows
        selected_idx = timeline_state.selected_row_idx

        if not flat_rows:
            lines.append(("class:dim", "  No timeline records\n"))
            return lines

        lines.append(("class:header", "  Timeline\n\n"))

        for row_idx, row in enumerate(flat_rows):
            row_type = row[0]
            is_selected = row_idx == selected_idx

            if row_type == "date_header":
                # Date header row (not selectable)
                date_str = row[1]
                lines.append(("class:dim", f"  -- {date_str} --\n\n"))

            elif row_type == "session":
                # Session row: (row_type, session_dict, session_num, takeaway_count)
                session_dict = row[1]
                session_num = row[2]
                lines.extend(self._render_session_row(session_dict, session_num, is_selected))

            elif row_type == "takeaway":
                # Takeaway row: (row_type, takeaway_dict, takeaway_num, is_last, parent_session_dict)
                takeaway_dict = row[1]
                takeaway_num = row[2]
                is_last = row[3]
                lines.extend(self._render_takeaway_row(takeaway_dict, takeaway_num, is_last, is_selected, is_standalone=False))

            elif row_type == "standalone_takeaway":
                # Standalone takeaway: (row_type, takeaway_dict)
                takeaway_dict = row[1]
                lines.extend(self._render_takeaway_row(takeaway_dict, 0, True, is_selected, is_standalone=True))

        return lines

    def _render_session_row(self, session_dict: dict, session_num: int, is_selected: bool) -> list:
        """Render a Session row."""
        lines = []

        # Get time info
        ended_at = session_dict.get("ended_at_utc")
        started_at = session_dict.get("started_at_utc")

        # Format time
        if ended_at:
            time_str = ended_at.strftime("%H:%M")
        else:
            time_str = "??:??"

        # Calculate duration
        if started_at and ended_at:
            duration_seconds = (ended_at - started_at).total_seconds()
            duration_min = int(duration_seconds // 60)
            duration_str = f"{duration_min}m"
        else:
            duration_str = "?m"

        # Get parent info
        parent_info = session_dict.get("parent_info", "")

        # Build display text
        prefix = "▸ " if is_selected else "  "
        display_text = f"{prefix}{time_str} {duration_str} Session {session_num}: {parent_info}\n"

        style = "class:selected" if is_selected else ""
        lines.append((style, display_text))

        return lines

    def _render_takeaway_row(self, takeaway_dict: dict, takeaway_num: int, is_last: bool, is_selected: bool, is_standalone: bool) -> list:
        """Render a Takeaway row with tree structure."""
        lines = []

        # Get time info
        created_at = takeaway_dict.get("created_at_utc")
        if created_at:
            time_str = created_at.strftime("%H:%M")
        else:
            time_str = "??:??"

        # Get takeaway type and title
        takeaway_type = takeaway_dict.get("type", "action")
        title = takeaway_dict.get("title", "")
        content = takeaway_dict.get("content", "")

        # Use title if available, otherwise truncate content
        display_text = title if title else (content[:30] + "..." if len(content) > 30 else content)

        if is_standalone:
            # Standalone takeaway (no parent session)
            parent_info = takeaway_dict.get("parent_info", "")
            prefix = "▸ " if is_selected else "  "
            line = f"{prefix}{time_str} Takeaway: [{takeaway_type}] {parent_info} · {display_text}\n"
        else:
            # Linked takeaway (under a session)
            tree_symbol = "└──" if is_last else "├──"
            prefix = "▸ " if is_selected else "  "
            # Indent for tree structure
            line = f"{prefix}  {tree_symbol} {time_str} Takeaway {takeaway_num}: [{takeaway_type}] · {display_text}\n"

        style = "class:selected" if is_selected else ""
        lines.append((style, line))

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

                # Render project row using README display format, right-aligned within box.
                content_width = self.box_width - 2
                segs = self._structure_line_segments(
                    item_type="project",
                    index_1based=proj_idx + 1,
                    item=project,
                    is_selected=is_project_selected,
                    width=content_width,
                )

                row_text = "".join(t for _, t in segs).rstrip("\n")
                row_text_width = self._display_width(row_text)
                pad = " " * max(0, content_width - row_text_width)

                lines.append(("", "│"))
                for style, text in segs:
                    lines.append((style, text.rstrip("\n")))
                if pad:
                    base_style = self._get_item_style(project, "project", is_project_selected)
                    lines.append((base_style, pad))
                lines.append(("", "│\n"))

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

