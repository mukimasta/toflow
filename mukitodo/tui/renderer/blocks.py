from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Literal

from mukitodo.tui.states.app_state import StructureLevel

from . import constants

Line = list[tuple[str, str]]
Lines = list[Line]


@dataclass(frozen=True)
class SelectedLine:
    line_idx: int


@dataclass(frozen=True)
class SelectedSpan:
    start_line_idx: int
    end_line_idx: int
    oversize_policy: Literal["anchor_top"] = "anchor_top"


@dataclass(frozen=True)
class ViewContent:
    lines: Lines
    selection: SelectedLine | SelectedSpan | None = None


@dataclass(frozen=True)
class RenderHelpers:
    # Low-level helpers
    display_width: Callable[[str], int]
    get_terminal_width: Callable[[], int]

    # Style helpers
    get_item_style: Callable[[dict, str, bool], str]
    get_archive_track_style: Callable[[dict, bool], str]
    get_archive_project_style: Callable[[dict, bool], str]

    # Row renderers (return a single-line segment list, no trailing newline)
    structure_line_segments: Callable[[str, int, dict, bool, int], list[tuple[str, str]]]

    # Convenience line constructors
    blank_line: Callable[[], Line]
    text_line: Callable[[str, str], Line]


# =============================================================================
# Structure
# =============================================================================


def structure_tracks_content(*, state, h: RenderHelpers) -> ViewContent:
    tracks = state.structure_state.current_tracks_list
    selected_idx = state.structure_state.selected_track_idx

    lines: Lines = []
    selection: SelectedLine | None = None

    if not tracks:
        lines.append(h.text_line("  No tracks. Press = to add", "class:dim"))
        return ViewContent(lines=lines, selection=None)

    lines.append(h.text_line("  Tracks", "class:header"))
    lines.append(h.blank_line())

    for idx, track in enumerate(tracks):
        is_selected = (selected_idx == idx)
        prefix = "▸ " if is_selected else "  "
        style = h.get_item_style(track, "track", is_selected)
        lines.append(h.text_line(f"{prefix}Track {idx + 1}: {track.get('name','')}", style))
        if is_selected:
            selection = SelectedLine(line_idx=len(lines) - 1)

    return ViewContent(lines=lines, selection=selection)


def structure_tracks_with_projects_content(*, state, h: RenderHelpers, level: StructureLevel, box_width: int) -> ViewContent:
    tracks_with_projects = state.structure_state.current_tracks_with_projects_list
    tracks = state.structure_state.current_tracks_list

    lines: Lines = []
    selection: SelectedLine | SelectedSpan | None = None

    if not tracks:
        lines.append(h.text_line("No tracks. Press = to add", "class:dim"))
        return ViewContent(lines=lines, selection=None)

    for track_idx, (track, projects) in enumerate(tracks_with_projects):
        is_track_selected = track_idx == state.structure_state.selected_track_idx

        block_lines, block_selection = _twp_track_box_block(
            state=state,
            h=h,
            level=level,
            box_width=box_width,
            track=track,
            projects=projects,
            track_idx=track_idx,
            is_track_selected=is_track_selected,
        )
        block_start = len(lines)
        lines.extend(block_lines)

        if block_selection is not None:
            if isinstance(block_selection, SelectedLine):
                selection = SelectedLine(line_idx=block_start + block_selection.line_idx)
            else:
                selection = SelectedSpan(
                    start_line_idx=block_start + block_selection.start_line_idx,
                    end_line_idx=block_start + block_selection.end_line_idx,
                    oversize_policy=block_selection.oversize_policy,
                )

        # Spacer between track boxes (kept outside span selection).
        lines.append(h.blank_line())

    return ViewContent(lines=lines, selection=selection)


def _twp_track_box_block(
    *,
    state,
    h: RenderHelpers,
    level: StructureLevel,
    box_width: int,
    track: dict,
    projects: list[dict],
    track_idx: int,
    is_track_selected: bool,
) -> tuple[Lines, SelectedLine | SelectedSpan | None]:
    block: Lines = []
    selection: SelectedLine | SelectedSpan | None = None

    if is_track_selected:
        track_style = "class:selected_track"
    else:
        track_style = h.get_item_style(track, "track", False) or "class:unselected_track"

    title = f" Track {track_idx + 1}: {track.get('name','')} "
    title_w = h.display_width(title)
    dash_count = max(1, box_width - 2 - 1 - title_w)
    top_line = "┌─" + title + "─" * dash_count + "┐"
    block.append(h.text_line(top_line, track_style))
    box_top_idx = 0

    content_width = box_width - 2
    if not projects:
        is_empty_focused = is_track_selected and level == StructureLevel.TRACKS_WITH_PROJECTS_P
        empty_prefix = "▸ " if is_empty_focused else "  "
        empty_display = f"{empty_prefix}(no projects)"
        empty_w = h.display_width(empty_display)
        pad = " " * max(0, content_width - empty_w)

        empty_style = "class:selected" if is_empty_focused else track_style
        block.append([("", "│"), (empty_style, empty_display + pad), ("", "│")])

        if level == StructureLevel.TRACKS_WITH_PROJECTS_T and is_track_selected:
            selection = SelectedSpan(start_line_idx=box_top_idx, end_line_idx=len(block), oversize_policy="anchor_top")
        if is_empty_focused:
            selection = SelectedLine(line_idx=len(block) - 1)
    else:
        for proj_idx, project in enumerate(projects):
            is_project_selected = (
                is_track_selected
                and level == StructureLevel.TRACKS_WITH_PROJECTS_P
                and proj_idx == state.structure_state.selected_project_idx
            )

            segs = h.structure_line_segments("project", proj_idx + 1, project, is_project_selected, content_width)
            row_text = "".join(t for _, t in segs)
            pad = " " * max(0, content_width - h.display_width(row_text))
            base_style = h.get_item_style(project, "project", is_project_selected)

            block.append([("", "│"), *segs, (base_style, pad), ("", "│")])
            if is_project_selected:
                selection = SelectedLine(line_idx=len(block) - 1)

        if level == StructureLevel.TRACKS_WITH_PROJECTS_T and is_track_selected:
            selection = SelectedSpan(start_line_idx=box_top_idx, end_line_idx=len(block), oversize_policy="anchor_top")

    bottom_line = "└" + "─" * (box_width - 2) + "┘"
    block.append(h.text_line(bottom_line, track_style))
    box_bottom_idx = len(block) - 1

    if isinstance(selection, SelectedSpan):
        selection = SelectedSpan(
            start_line_idx=selection.start_line_idx,
            end_line_idx=box_bottom_idx,
            oversize_policy=selection.oversize_policy,
        )

    return block, selection


def structure_todos_content(*, state, h: RenderHelpers) -> ViewContent:
    todos = state.structure_state.current_todos_list
    selected_idx = state.structure_state.selected_todo_idx

    project_name = "Unknown"
    project_id = state.structure_state.current_project_id
    if project_id is not None:
        for proj in state.structure_state.current_projects_list:
            if proj.get("id") == project_id:
                project_name = proj.get("name", "Unknown")
                break

    lines: Lines = []
    selection: SelectedLine | None = None

    lines.append(h.text_line(f"  Project: {project_name}", "class:header"))
    lines.append(h.blank_line())

    if project_id is None:
        lines.append(h.text_line("  No project selected", "class:dim"))
        return ViewContent(lines=lines, selection=None)

    if not todos:
        lines.append(h.text_line("  No items. Press = to add items.", "class:dim"))
        return ViewContent(lines=lines, selection=None)

    indent = "  "
    width = max(constants.LIST_MIN_TERMINAL_WIDTH, h.get_terminal_width() - 2)
    content_width = max(constants.LIST_MIN_CONTENT_WIDTH, width - h.display_width(indent))

    for idx, todo in enumerate(todos):
        is_selected = (selected_idx == idx)
        segs = h.structure_line_segments("todo", idx + 1, todo, is_selected, content_width)
        lines.append([("", indent), *segs])
        if is_selected:
            selection = SelectedLine(line_idx=len(lines) - 1)

    return ViewContent(lines=lines, selection=selection)


# =============================================================================
# Box
# =============================================================================


def box_content(*, state, h: RenderHelpers) -> ViewContent:
    box_state = state.box_state
    subview = box_state.subview

    lines: Lines = []
    selection: SelectedLine | None = None

    lines.append(h.text_line("  BOX", "class:header"))
    lines.append(h.blank_line())
    lines.append(h.text_line(f"  Subview: {subview.value.upper()}   ([ / ] switch)", "class:dim"))
    lines.append(h.blank_line())

    width = max(constants.LIST_MIN_TERMINAL_WIDTH, h.get_terminal_width() - 2)
    indent = "  "
    content_width = max(constants.LIST_MIN_CONTENT_WIDTH, width - h.display_width(indent))

    if subview.value == "todos":
        items = box_state.current_box_todos_list
        selected_idx = box_state.selected_todo_idx
        item_type = "todo"
        empty_label = "No box todos. Press = to add"
    else:
        items = box_state.current_box_ideas_list
        selected_idx = box_state.selected_idea_idx
        item_type = "idea"
        empty_label = "No ideas. Press = to add"

    if not items:
        lines.append(h.text_line(f"  {empty_label}", "class:dim"))
        return ViewContent(lines=lines, selection=None)

    for idx, item in enumerate(items):
        is_selected = (selected_idx == idx)
        segs = h.structure_line_segments(item_type, idx + 1, item, is_selected, content_width)
        lines.append([("", indent), *segs])
        if is_selected:
            selection = SelectedLine(line_idx=len(lines) - 1)

    return ViewContent(lines=lines, selection=selection)


# =============================================================================
# Info
# =============================================================================


def info_content(*, state, h: RenderHelpers) -> ViewContent:
    item_data = state.info_state.field_dict
    selected_idx = state.info_state.selected_field_idx

    lines: Lines = []
    selection: SelectedLine | None = None

    if not item_data:
        lines.append(h.text_line("  No field data available", "class:error"))
        return ViewContent(lines=lines, selection=None)

    for idx, (field_name, value) in enumerate(item_data.items()):
        if value is None:
            display_value = "None"
        elif isinstance(value, datetime):
            display_value = value.strftime("%Y-%m-%d %H:%M:%S")
        else:
            display_value = str(value)

        is_selected = (selected_idx == idx)
        prefix = "▸ " if is_selected else "  "
        style = "class:selected" if is_selected else ""
        lines.append(h.text_line(f"{prefix}{field_name}: {display_value}", style))
        if is_selected:
            selection = SelectedLine(line_idx=len(lines) - 1)

    return ViewContent(lines=lines, selection=selection)


# =============================================================================
# Timeline
# =============================================================================


def timeline_content(*, state, h: RenderHelpers) -> ViewContent:
    timeline_state = state.timeline_state
    flat_rows = timeline_state.flat_rows
    selected_row_idx = timeline_state.selected_row_idx

    lines: Lines = []
    selection: SelectedLine | None = None

    if not flat_rows:
        lines.append(h.text_line("  No timeline records", "class:dim"))
        return ViewContent(lines=lines, selection=None)

    lines.append(h.text_line("  Timeline", "class:header"))
    lines.append(h.blank_line())

    for row_idx, row in enumerate(flat_rows):
        row_type = row[0]
        is_selected = (row_idx == selected_row_idx)

        if row_type == "date_header":
            date_str = row[1]
            lines.append(h.text_line(f"  -- {date_str} --", "class:dim"))
            lines.append(h.blank_line())
            continue

        if row_type == "session":
            line = _timeline_session_line(row[1], row[2], is_selected=is_selected)
            lines.append(line)
            if is_selected:
                selection = SelectedLine(line_idx=len(lines) - 1)
            continue

        if row_type == "takeaway":
            line = _timeline_takeaway_line(row[1], row[2], is_last=row[3], is_selected=is_selected, is_standalone=False)
            lines.append(line)
            if is_selected:
                selection = SelectedLine(line_idx=len(lines) - 1)
            continue

        if row_type == "standalone_takeaway":
            line = _timeline_takeaway_line(row[1], 0, is_last=True, is_selected=is_selected, is_standalone=True)
            lines.append(line)
            if is_selected:
                selection = SelectedLine(line_idx=len(lines) - 1)
            continue

    return ViewContent(lines=lines, selection=selection)


def _timeline_session_line(session_dict: dict, session_num: int, *, is_selected: bool) -> Line:
    ended_at = session_dict.get("ended_at_utc")
    started_at = session_dict.get("started_at_utc")
    time_str = ended_at.strftime("%H:%M") if ended_at else "??:??"
    if started_at and ended_at:
        duration_min = int((ended_at - started_at).total_seconds() // 60)
        duration_str = f"{duration_min}m"
    else:
        duration_str = "?m"
    parent_info = session_dict.get("parent_info", "")
    prefix = "▸ " if is_selected else "  "
    style = "class:selected" if is_selected else ""
    return [(style, f"{prefix}{time_str} {duration_str} Session {session_num}: {parent_info}")]


def _timeline_takeaway_line(
    takeaway_dict: dict,
    takeaway_num: int,
    *,
    is_last: bool,
    is_selected: bool,
    is_standalone: bool,
) -> Line:
    created_at = takeaway_dict.get("created_at_utc")
    time_str = created_at.strftime("%H:%M") if created_at else "??:??"
    takeaway_type = takeaway_dict.get("type", "action")
    title = takeaway_dict.get("title", "")
    content = takeaway_dict.get("content", "")
    preview_chars = constants.TIMELINE_TAKEAWAY_PREVIEW_CHARS
    display_text = title if title else (content[:preview_chars] + "..." if len(content) > preview_chars else content)

    prefix = "▸ " if is_selected else "  "
    style = "class:selected" if is_selected else ""
    if is_standalone:
        parent_info = takeaway_dict.get("parent_info", "")
        text = f"{prefix}{time_str} Takeaway: [{takeaway_type}] {parent_info} · {display_text}"
    else:
        tree_symbol = "└──" if is_last else "├──"
        text = f"{prefix}  {tree_symbol} {time_str} Takeaway {takeaway_num}: [{takeaway_type}] · {display_text}"
    return [(style, text)]


# =============================================================================
# Archive
# =============================================================================


def archive_content(*, state, h: RenderHelpers) -> ViewContent:
    archive_data = state.archive_state.archive_data
    selected_idx = state.archive_state.selected_idx

    lines: Lines = []
    selection: SelectedLine | None = None

    if not archive_data or (not archive_data.get("tracks") and not archive_data.get("ideas")):
        lines.append(h.text_line("  No archived items", "class:dim"))
        return ViewContent(lines=lines, selection=None)

    lines.append(h.text_line("  Archive", "class:header"))
    lines.append(h.blank_line())

    flat_idx = 0
    for track_item in archive_data.get("tracks", []):
        is_selected = (flat_idx == selected_idx)
        prefix = "▸ " if is_selected else "  "
        style = h.get_archive_track_style(track_item, is_selected)
        track_status = track_item["track"]["status"]
        suffix = f" ({track_status})" if not track_item["is_archived"] else ""
        lines.append(h.text_line(f"{prefix}Track: {track_item['track']['name']}{suffix}", style))
        if is_selected:
            selection = SelectedLine(line_idx=len(lines) - 1)
        flat_idx += 1

        for proj_item in track_item.get("projects", []):
            is_selected = (flat_idx == selected_idx)
            prefix = "▸ " if is_selected else "  "
            style = h.get_archive_project_style(proj_item, is_selected)
            project_status = proj_item["project"]["status"]
            suffix = f" ({project_status})" if not proj_item["is_archived"] else ""
            marker = " ✓" if project_status == "finished" else ""
            lines.append(h.text_line(f"{prefix}  Project: {proj_item['project']['name']}{marker}{suffix}", style))
            if is_selected:
                selection = SelectedLine(line_idx=len(lines) - 1)
            flat_idx += 1

            for todo in proj_item.get("todos", []):
                is_selected = (flat_idx == selected_idx)
                prefix = "▸ " if is_selected else "  "
                if is_selected:
                    style = "class:selected"
                else:
                    style = f"class:todo.{todo.get('status','active')}"
                marker = "✓" if todo.get("status") == "done" else "○"
                lines.append(h.text_line(f"{prefix}    {marker} {todo.get('name','')}", style))
                if is_selected:
                    selection = SelectedLine(line_idx=len(lines) - 1)
                flat_idx += 1

        lines.append(h.blank_line())

    if archive_data.get("ideas"):
        lines.append(h.text_line("  Archived Ideas", "class:header"))
        lines.append(h.blank_line())
        for idea in archive_data.get("ideas", []):
            is_selected = (flat_idx == selected_idx)
            prefix = "▸ " if is_selected else "  "
            style = "class:selected" if is_selected else "class:idea.archived"
            lines.append(h.text_line(f"{prefix}Idea: {idea.get('name','')} (archived)", style))
            if is_selected:
                selection = SelectedLine(line_idx=len(lines) - 1)
            flat_idx += 1
        lines.append(h.blank_line())

    if archive_data.get("box_todos"):
        lines.append(h.text_line("  Archived Box Todos", "class:header"))
        lines.append(h.blank_line())
        for todo in archive_data.get("box_todos", []):
            is_selected = (flat_idx == selected_idx)
            prefix = "▸ " if is_selected else "  "
            if is_selected:
                style = "class:selected"
            else:
                style = f"class:todo.{todo.get('status','active')}"
            marker = "✓" if todo.get("status") == "done" else "○"
            lines.append(h.text_line(f"{prefix}{marker} Todo: {todo.get('name','')}", style))
            if is_selected:
                selection = SelectedLine(line_idx=len(lines) - 1)
            flat_idx += 1

    return ViewContent(lines=lines, selection=selection)


