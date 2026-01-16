import unicodedata
from datetime import datetime

from prompt_toolkit.styles import Style

from mukitodo.tui.states.app_state import AppState, StructureLevel, UIMode, View
from mukitodo.tui.states.now_state import TimerStateEnum, TimerPhaseEnum
from mukitodo.tui.states.input_state import FormField, FormType, InputPurpose

from . import blocks
from .blocks import Line, Lines, RenderHelpers, SelectedLine, SelectedSpan, ViewContent
from . import constants


class Renderer:
    def __init__(self, state: "AppState"):
        self.state = state

        # == Render Context =================
        self.box_width = constants.STRUCTURE_TWP_BOX_WIDTH
        self.separator_width = constants.SEPARATOR_LINE_WIDTH
        # Per-view viewport start line (implicit scrolling without scrollbars).
        # Keyed by (View, optional subkey like StructureLevel/BoxSubview).
        self._viewport_start: dict[tuple, int] = {}

        # Shared viewport keys (keep switching stable between related sub-levels).
        self._viewport_key_tracks_with_projects = (View.STRUCTURE, "TRACKS_WITH_PROJECTS")

        # Blocks layer helpers (Renderer owns helper implementations; blocks build view content).
        self._blocks_helpers = RenderHelpers(
            display_width=self._display_width,
            get_terminal_width=lambda: self._get_terminal_width(),
            get_item_style=self._get_item_style,
            get_archive_track_style=self._get_archive_track_style,
            get_archive_project_style=self._get_archive_project_style,
            structure_line_segments=lambda item_type, index_1based, item, is_selected, width: self._structure_line_segments(
                item_type=item_type,
                index_1based=index_1based,
                item=item,
                is_selected=is_selected,
                width=width,
            ),
            blank_line=self._blank_line,
            text_line=lambda text, style="": self._text_line(text, style),
        )





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
            content = self._get_structure_tracks_view_content_lines()
            return self._render_with_viewport(viewport_key=(View.STRUCTURE, StructureLevel.TRACKS), content=content)
        elif self.state.structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS_T:
            content = self._get_structure_tracks_with_projects_view_content_lines(level=StructureLevel.TRACKS_WITH_PROJECTS_T)
            return self._render_with_viewport(viewport_key=self._viewport_key_tracks_with_projects, content=content)
        elif self.state.structure_state.structure_level == StructureLevel.TRACKS_WITH_PROJECTS_P:
            content = self._get_structure_tracks_with_projects_view_content_lines(level=StructureLevel.TRACKS_WITH_PROJECTS_P)
            return self._render_with_viewport(viewport_key=self._viewport_key_tracks_with_projects, content=content)
        else:  # TODOS
            content = self._get_structure_todos_view_content_lines()
            return self._render_with_viewport(viewport_key=(View.STRUCTURE, StructureLevel.TODOS), content=content)

    def render_info_view_content(self) -> list:
        """Render INFO view content."""
        content = self._get_info_view_content_lines()
        return self._render_with_viewport(viewport_key=(View.INFO,), content=content)

    def render_archive_view_content(self) -> list:
        """Render ARCHIVE view content."""
        content = self._get_archive_view_content_lines()
        return self._render_with_viewport(viewport_key=(View.ARCHIVE,), content=content)

    def render_box_view_content(self) -> list:
        """Render BOX view content."""
        content = self._get_box_view_content_lines()
        subval = getattr(getattr(self.state.box_state, "subview", None), "value", "unknown")
        return self._render_with_viewport(viewport_key=(View.BOX, subval), content=content)

    def render_timeline_view_content(self) -> list:
        """Render TIMELINE view content."""
        content = self._get_timeline_view_content_lines()
        return self._render_with_viewport(viewport_key=(View.TIMELINE,), content=content)

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
            if now_state.timer_phase == TimerPhaseEnum.BREAK:
                # BREAK: no adjust; r returns to WORK idle 25:00.
                if now_state.timer_state == TimerStateEnum.IDLE:
                    parts.append("[Space] Start Break")
                    parts.append("[r] Reset to Work")
                elif now_state.timer_state == TimerStateEnum.RUNNING:
                    parts.append("[Space] Pause Break")
                    parts.append("[r] Reset to Work")
                else:  # PAUSED
                    parts.append("[Space] Resume Break")
                    parts.append("[r] Reset to Work")
            else:
                # WORK phase
                if now_state.timer_state == TimerStateEnum.IDLE:
                    if now_state.work_timeup_latched:
                        # At 00:00 latch: Space is disabled; allow Enter or r.
                        parts.append("[Enter] Finish")
                        parts.append("[r] Reset")
                    else:
                        parts.append("[Space] Start")
                        parts.append("[+/-] Adjust")
                        parts.append("[Enter] Finish")
                elif now_state.timer_state == TimerStateEnum.RUNNING:
                    parts.append("[Space] Pause")
                    parts.append("[r] Reset")
                    parts.append("[Enter] Finish")
                else:  # PAUSED
                    parts.append("[Space] Resume")
                    parts.append("[r] Reset")
                    parts.append("[Enter] Finish")
            
            # Navigation
            parts.append("[Tab] STRUCTURE")
            parts.append("[' ] Timeline")
            parts.append("[i] Info")
            parts.append("[q] Quit")
            
            return [("class:dim", "  " + "  ".join(parts))]
        

        if self.state.view == View.INFO:
            parts = ["[↑↓] move", "[i/Esc/q] back"]
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

            parts.extend(["[=/+] add", "[p] pin", "[Backspace] delete"])
            parts.extend(["[Tab] NOW", "[' ] timeline", "[i] info", "[q] quit"])

            return [("class:dim", "  " + "  ".join(parts))]

        if self.state.view == View.ARCHIVE:
            parts = ["[↑↓] move", "[a] unarchive", "[Backspace] delete", "[i] detail", "[`/Esc/q] exit"]
            return [("class:dim", "  " + "  ".join(parts))]

        if self.state.view == View.BOX:
            parts = [
                "[↑↓] move",
                "[[]] todos",
                "[]] ideas",
                "[=/+] add",
                "[r] edit",
                "[a] archive",
                "[Backspace] delete",
                "[m] move/promote",
                "[i] detail",
                "[Esc/q] back",
            ]
            return [("class:dim", "  " + "  ".join(parts))]

        if self.state.view == View.TIMELINE:
            parts = ["[↑↓] move", "[i] detail", "[Backspace] delete", "['/Esc/q] exit"]
            return [("class:dim", "  " + "  ".join(parts))]

        # Default fallback
        return [("class:dim", "  [q] Quit/Back")]

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

        if form_type == FormType.NOW_STAGE_UPDATE:
            return [("class:mode", "[Finish Session: Stages Done]")]

        verb = "New" if purpose == InputPurpose.ADD else "Edit"
        label = form_type.value.replace("_", " ").title()
        return [("class:mode", f"[{verb} {label}]")]

    def render_input_field_label(self, label: str) -> list[tuple[str, str]]:
        return [("class:dim", label)]

    def render_input_text_value(self, field: FormField) -> list[tuple[str, str]]:
        """Non-active display for a text field (active state uses BufferControl)."""
        input_state = self.state.input_state
        value = input_state.get_field_str(field)
        style = "class:selected" if input_state.current_field == field else ""
        return [(style, value)]

    def render_input_chip(self, field: FormField, label: str) -> list[tuple[str, str]]:
        """Compact chip, highlighted when selected."""
        input_state = self.state.input_state
        value = input_state.get_field_display(field)
        style = "class:selected" if input_state.current_field == field else "class:dim"

        if field == FormField.STATUS:
            s = str(value or "active")
            display = s.replace("_", " ").title()
            return [(style, f"[{display}]")]

        if field in (FormField.TOTAL_STAGES, FormField.CURRENT_STAGE):
            # Stage display: always show as [C/T] (e.g. [3/10]).
            try:
                total = int(input_state.get_field_display(FormField.TOTAL_STAGES) or 1)
            except Exception:
                total = 1
            try:
                cur = int(input_state.get_field_display(FormField.CURRENT_STAGE) or 0)
            except Exception:
                cur = 0
            total = max(1, total)
            cur = max(0, min(cur, total))

            # Highlight only the selected side:
            # - current_stage selected -> highlight left number
            # - total_stages selected -> highlight right number
            left_style = "class:selected" if input_state.current_field == FormField.CURRENT_STAGE else "class:dim"
            right_style = "class:selected" if input_state.current_field == FormField.TOTAL_STAGES else "class:dim"
            bracket_style = "class:dim"
            return [
                (bracket_style, "["),
                (left_style, str(cur)),
                (bracket_style, "/"),
                (right_style, str(total)),
                (bracket_style, "]"),
            ]

        if field == FormField.STAGES_DONE:
            # Display as a single numeric chip: [+k]
            # (Used by NOW finish-session stage update prompt)
            n = str(value or "0")
            return [("class:selected" if input_state.current_field == field else "class:dim", f"[+{n}]")]

        if field in (FormField.WILLINGNESS_HINT, FormField.IMPORTANCE_HINT, FormField.URGENCY_HINT):
            icon = {
                FormField.WILLINGNESS_HINT: "♥",
                FormField.IMPORTANCE_HINT: "⭑",
                FormField.URGENCY_HINT: "⚡",
            }[field]
            bar = str(value or "▁")
            return [(style, f"[{icon} {bar}]")]

        if field == FormField.MATURITY_HINT:
            bar = str(value or "▁")
            return [(style, f"[M {bar}]")]

        if label:
            return [(style, f"[{label}:{value}]")]
        return [(style, f"[{value}]")]

    # == Structure Line Formatting ======================================

    _STATUS_ICON_MAP = {
        "active": "○",
        "sleeping": "z",
        "finished": "◉",
        "done": "◉",
        "cancelled": "×",
        "deprecated": "×",
        "promoted": "⇡",
    }

    def _get_terminal_width(self, fallback: int = 80) -> int:
        """Best-effort terminal width for alignment. Safe to call without an active app."""
        try:
            from prompt_toolkit.application.current import get_app
            cols = get_app().output.get_size().columns
            return int(cols) if cols and cols > 0 else fallback
        except Exception:
            return fallback

    def _get_terminal_height(self, fallback: int = 24) -> int:
        """Best-effort terminal height. Safe to call without an active app."""
        try:
            from prompt_toolkit.application.current import get_app
            rows = get_app().output.get_size().rows
            return int(rows) if rows and rows > 0 else fallback
        except Exception:
            return fallback

    def _reserved_bottom_rows(self) -> int:
        """
        Rows reserved outside the main view content area:
        - separator: 1
        - status bar: 1
        - command mode bar: +1
        - input mode panel: +2
        """
        reserved = 2
        if self.state.ui_mode == UIMode.COMMAND:
            reserved += 1
        if self.state.ui_mode == UIMode.INPUT:
            reserved += 2
        return reserved

    def _viewport_height(self) -> int:
        return max(1, self._get_terminal_height() - self._reserved_bottom_rows())

    # == Viewport (Lines) ======================================================

    def _flatten_lines(self, lines: Lines) -> list[tuple[str, str]]:
        """Flatten line segments into prompt-toolkit formatted text, appending '\\n' per line."""
        out: list[tuple[str, str]] = []
        for line in lines:
            out.extend(line if line else [("", "")])
            out.append(("", "\n"))
        return out

    def _render_with_viewport(
        self,
        *,
        viewport_key: tuple,
        content: ViewContent,
        margin: int = constants.VIEWPORT_CURSOR_MARGIN_LINES,
    ) -> list[tuple[str, str]]:
        """
        Viewport wrapper for all non-NOW views:
        - takes prebuilt lines + explicit selection (derived from state)
        - computes stable start_line (implicit scroll)
        - returns flattened formatted text
        """
        full_lines = content.lines if content.lines else [[("class:dim", "")]]
        total = len(full_lines)
        viewport_h = self._viewport_height()

        def _clamp_start(x: int) -> int:
            return max(0, min(int(x), max(0, total - viewport_h)))

        if total <= viewport_h:
            self._viewport_start[viewport_key] = 0
            return self._flatten_lines(full_lines)

        start = _clamp_start(self._viewport_start.get(viewport_key, 0))

        selection = content.selection
        if isinstance(selection, SelectedSpan):
            span_start = max(0, min(selection.start_line_idx, total - 1))
            span_end = max(0, min(selection.end_line_idx, total - 1))
            if span_end < span_start:
                span_start, span_end = span_end, span_start

            span_len = span_end - span_start + 1
            if span_len <= viewport_h:
                visible_top = start
                visible_bottom = start + viewport_h - 1
                if span_start < visible_top:
                    start = span_start
                elif span_end > visible_bottom:
                    start = span_end - (viewport_h - 1)
                start = _clamp_start(start)
            else:
                # Oversize span (TWP_T): keep the title line visible.
                start = _clamp_start(span_start)

        elif isinstance(selection, SelectedLine):
            sel = max(0, min(selection.line_idx, total - 1))
            top = start + margin
            bottom = start + viewport_h - margin - 1
            if sel < top:
                start = sel - margin
            elif sel > bottom:
                start = sel - (viewport_h - margin - 1)
            start = _clamp_start(start)

        else:
            # No selection: keep previous start (clamped).
            start = _clamp_start(start)

        self._viewport_start[viewport_key] = start
        visible = full_lines[start : start + viewport_h]
        return self._flatten_lines(visible)

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
        if item_type in ("project", "todo"):
            if session_count > 0:
                flags.append(f"[⧗{session_count}]")
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
        if item_type in ("project", "todo") and bool(item.get("pinned")):
            icon = "✜"
        else:
            icon = self._STATUS_ICON_MAP.get(status, "○")

        left = f"{icon} {item_type.capitalize()} {index_1based}: {item.get('name','')}"

        # Stage progress (Todos only): always display.
        if item_type == "todo":
            try:
                total = int(item.get("total_stages") or 1)
            except Exception:
                total = 1
            try:
                cur = int(item.get("current_stage") or 0)
            except Exception:
                cur = 0
            total = max(1, total)
            cur = max(0, min(cur, total))
            if total > 1:
                left = left + f" [{cur}/{total}]"

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
            return segments

        # Fallback: if it doesn't fit, drop right_text.
        text = left
        if self._display_width(text) > width:
            text = self._truncate_to_display_width(text, width)
        return [(base_style, text)]



    # == View Renderers =================

    def _render_now_view(self) -> list:
        """Render NOW view with centered box layout."""
        lines = []
        box_width = constants.NOW_VIEW_BOX_WIDTH
        
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
        """Deprecated: old flat segment renderer (removed)."""
        return []

    # == View Content (Lines) ==================================================

    def _blank_line(self) -> Line:
        return [("", "")]

    def _text_line(self, text: str, style: str = "") -> Line:
        return [(style, text)] if style else [("", text)]

    def _prefixed_line(self, *, prefix: str, text: str, style: str) -> Line:
        return [(style, f"{prefix}{text}")]

    def _get_structure_tracks_view_content_lines(self) -> ViewContent:
        return blocks.structure_tracks_content(state=self.state, h=self._blocks_helpers)

    def _get_structure_tracks_with_projects_view_content_lines(self, *, level: StructureLevel) -> ViewContent:
        return blocks.structure_tracks_with_projects_content(
            state=self.state,
            h=self._blocks_helpers,
            level=level,
            box_width=self.box_width,
        )

    def _get_structure_todos_view_content_lines(self) -> ViewContent:
        return blocks.structure_todos_content(state=self.state, h=self._blocks_helpers)

    def _get_info_view_content_lines(self) -> ViewContent:
        return blocks.info_content(state=self.state, h=self._blocks_helpers)

    def _get_box_view_content_lines(self) -> ViewContent:
        return blocks.box_content(state=self.state, h=self._blocks_helpers)

    def _get_timeline_view_content_lines(self) -> ViewContent:
        return blocks.timeline_content(state=self.state, h=self._blocks_helpers)

    def _get_archive_view_content_lines(self) -> ViewContent:
        return blocks.archive_content(state=self.state, h=self._blocks_helpers)


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
            try:
                total = int(todo.get("total_stages") or 1)
            except Exception:
                total = 1
            try:
                cur = int(todo.get("current_stage") or 0)
            except Exception:
                cur = 0
            total = max(1, total)
            cur = max(0, min(cur, total))
            progress = f" [{cur}/{total}]"
            return [
                ("", f"{project['name']}"),
                ("", f"{marker} {todo['name']}{progress}")
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

        # Phase-aware status.
        if now_state.timer_phase == TimerPhaseEnum.BREAK:
            if now_state.timer_state == TimerStateEnum.RUNNING:
                return ("class:dim", "▶ Break")
            if now_state.timer_state == TimerStateEnum.PAUSED:
                return ("class:dim", "⏸  Break")
            return ("class:dim", "☕ Break")

        # WORK phase
        if now_state.work_timeup_latched and now_state.timer_state == TimerStateEnum.IDLE:
            return ("class:dim", "⏰ Time up")
        if now_state.timer_state == TimerStateEnum.RUNNING:
            return ("class:dim", "▶ Working")
        if now_state.timer_state == TimerStateEnum.PAUSED:
            return ("class:dim", "⏸  Paused")

        # Check todo status from cached data
        todo = now_state.current_todo_dict
        if todo and todo["status"] == "done":
            return ("class:dim", "✓ Finished")

        return ("class:dim", "⏱")


    # Blocks for Structure View are built as Lines in:
    # - _get_structure_*_view_content_lines()
    # - _twp_track_box_block_lines()







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

    def _separator_block(self, width: int = constants.SEPARATOR_LINE_WIDTH) -> list:
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

