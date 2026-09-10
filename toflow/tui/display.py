"""Display — viewport clipping, content rendering, styles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.styles import Style

from toflow.tui.state import PrimaryView
from toflow.tui.pane.base import FormattedText, Lines
from toflow.tui.text_width import take_by_width, text_width

if TYPE_CHECKING:
    from toflow.models import FieldSpec
    from toflow.tui.input.form import InputForm
    from toflow.tui.state import AppState

VIEWPORT_MARGIN = 2


# -- Line operations --


def flatten(lines: Lines) -> FormattedText:
    """Join lines into flat FormattedText with \\n separators for prompt_toolkit."""
    out: FormattedText = []
    for line in lines:
        out.extend(line)
        out.append(("", "\n"))
    return out


def clip_to_viewport(
    lines: Lines,
    viewport_height: int,
    selected_line: int | None,
    prev_start: int = 0,
    *,
    block_range: tuple[int, int] | None = None,
) -> tuple[Lines, int]:
    """Clip lines to fit viewport, keeping selected line visible.

    When block_range is provided and the selection lies within it, prefer showing
    the block from its top (header) so the box structure stays intact.
    """
    total = len(lines)
    if total <= viewport_height:
        return lines, 0

    start = max(0, min(prev_start, total - viewport_height))

    if selected_line is not None:
        sel = max(0, min(selected_line, total - 1))
        top = start + VIEWPORT_MARGIN
        bottom = start + viewport_height - VIEWPORT_MARGIN - 1
        if sel < top:
            start = max(0, sel - VIEWPORT_MARGIN)
        elif sel > bottom:
            start = sel - (viewport_height - VIEWPORT_MARGIN - 1)
        start = max(0, min(start, total - viewport_height))

        # Block-aware: only override when block would be cut (truncated)
        if block_range is not None:
            b_start, b_end = block_range
            if b_start <= sel <= b_end:
                block_visible = (b_start >= start) and (b_end < start + viewport_height)
                if not block_visible:
                    block_h = b_end - b_start + 1
                    if block_h <= viewport_height:
                        start = min(b_start, max(0, total - viewport_height))
                    else:
                        start = b_start
                    start = max(0, min(start, total - viewport_height))

    return lines[start : start + viewport_height], start


def truncate_lines(lines: Lines, width: int) -> Lines:
    """Truncate lines exceeding terminal width, adding … for overflow."""
    if width <= 0:
        return [[("", "")] for _ in lines]

    out: Lines = []
    for line in lines:
        line_len = sum(text_width(t) for _, t in line)
        if line_len <= width:
            out.append(line)
        else:
            truncated: FormattedText = []
            remaining = width - 1  # reserve 1 for …
            for style, text in line:
                if remaining <= 0:
                    break
                part_w = text_width(text)
                if part_w <= remaining:
                    truncated.append((style, text))
                    remaining -= part_w
                else:
                    truncated.append((style, take_by_width(text, remaining)))
                    remaining = 0
            truncated.append(("", "…"))
            out.append(truncated)
    return out


def apply_zen_layout(lines: Lines, width: int, height: int) -> Lines:
    """Center content block both horizontally and vertically."""
    if height <= 0:
        return []
    if width <= 0:
        return [[("", "")] for _ in range(height)]

    if not lines:
        lines = [[("", "")]]

    centered: Lines = []
    for line in lines:
        line_w = sum(text_width(text) for _, text in line)
        pad_left = max(0, (width - line_w) // 2)
        if pad_left > 0:
            centered.append([("", " " * pad_left), *line])
        else:
            centered.append(line)

    if len(centered) >= height:
        return centered[:height]

    pad_top = (height - len(centered)) // 2
    pad_bottom = height - len(centered) - pad_top
    empty = [("", "")]
    return ([empty] * pad_top) + centered + ([empty] * pad_bottom)


# -- Content renderers --


def render_title(state: AppState) -> FormattedText:
    """Title bar from current navigation context."""
    if state.modal is not None:
        return [("", f" {state.modal.title}")]
    if state.secondary is not None:
        return [("", f" {state.secondary.title}")]
    if state.primary == PrimaryView.NOW:
        return [("", " NOW")]
    # breadcrumb = " > ".join(v.title for v in state.structure_stack)
    return [("", f" {state.current_view.title}")]


def render_status(
    *, is_confirm: bool = False, last_result=None, status_hint: str = ""
) -> FormattedText:
    """Status bar content."""
    if is_confirm:
        return [
            ("class:warning reverse", " CONFIRM "),
            ("", " "),
            ("class:warning", "Press same key to confirm, any other to cancel"),
        ]
    if last_result and last_result.message:
        style = "class:success" if last_result.success else "class:error"
        return [(style, f"  {last_result.message}")]
    return [("class:dim", f"  {status_hint}")]


FORM_LABEL_W = 12


def render_input_form_lines(
    form: InputForm,
    mode_label: str = "EDIT",
    entity_label: str = "",
    *,
    width: int = 80,
) -> Lines:
    """Render multi-field form as a clean vertical list.

     Edit Project
     ▸ Title       Q1 Plan|
       Desc        Daily work
       Deadline    2025-03-01
       Will ▅      Imp █       Urg ▂

    Long text fields wrap within the terminal width (continuation lines
    indent under the value column).
    """
    header = f" {mode_label} {entity_label}".strip()
    lines: Lines = []

    # -- Header --
    lines.append([("class:form.header", f" {header}")])

    # -- Separate text/date fields from chip fields --
    text_fields: list[tuple[int, FieldSpec]] = []
    chip_fields: list[tuple[int, FieldSpec]] = []
    for i, spec in enumerate(form.fields):
        if spec.widget in ("chip", "select"):
            chip_fields.append((i, spec))
        else:
            text_fields.append((i, spec))

    # -- Text/date field rows (text may wrap to multiple lines) --
    for i, spec in text_fields:
        is_active = i == form.cursor
        prefix = " ▸ " if is_active else "   "
        label = spec.label.ljust(FORM_LABEL_W)
        value_width = max(1, width - text_width(prefix) - text_width(label))
        row_lines = form.render_row(
            spec, active=is_active, prefix=prefix, label=label, value_width=value_width
        )
        lines.extend(row_lines)

    # -- Chip fields row (grouped on one line) --
    if chip_fields:
        # Check if any chip is active for prefix
        any_chip_active = any(i == form.cursor for i, _ in chip_fields)
        prefix = " ▸ " if any_chip_active else "   "
        chip_line: FormattedText = [("", prefix)]
        for i, spec in chip_fields:
            is_active = i == form.cursor
            chip_line.extend(form.render_chip(spec, active=is_active))
            chip_line.append(("", "      "))
        lines.append(chip_line)

    return lines


# -- Style --


APP_STYLE = Style.from_dict({
    "dim": "ansibrightblack",
    "item.icon": "",
    "item.title": "",
    "item.meta": "ansibrightblack",
    "item.tag": "ansicyan",
    "item.dim": "ansibrightblack",
    "item.done": "ansibrightblack",
    "item.cancelled": "ansibrightblack strike",
    "item.pinned": "bold ansiyellow",
    "selected": "reverse",
    "selected_in_box": "bold ansiyellow",
    "selected_track": "bold ansicyan",
    "unselected_track": "ansibrightblack",
    "title": "bold",
    "header": "bold ansiblue",
    "success": "ansigreen",
    "error": "ansired",
    "warning": "ansiyellow",
    "separator": "ansibrightblack",
    "mode": "bg:ansiblue ansiwhite",
    "form.header": "bold ansiblue",
    "form.active": "bold",
    "form.dim": "ansibrightblack",
    "form.value": "",
    "form.value.active": "reverse",
    "form.cursor": "reverse",
    "form.selection": "reverse ansicyan",
    "hint.0": "ansibrightblack",
    "hint.1": "ansicyan",
    "hint.2": "ansiyellow",
    "hint.3": "bold ansired",
    "track.active": "",
    "track.sleeping": "ansibrightblack",
    "project.active": "",
    "project.sleeping": "ansibrightblack",
    "project.finished": "ansibrightblack",
    "project.cancelled": "ansibrightblack strike",
    "todo.active": "",
    "todo.sleeping": "ansibrightblack",
    "todo.done": "ansibrightblack",
    "todo.cancelled": "ansibrightblack strike",
})
