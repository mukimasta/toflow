"""Input widgets - per-field behavior and rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from prompt_toolkit.buffer import Buffer

from toflow.models import FieldSpec
from toflow.tui.input.intent import InputIntent
from toflow.tui.pane.base import FormattedText, Lines
from toflow.tui.text_width import wrap_text_lines

if TYPE_CHECKING:
    from toflow.tui.input.form import InputForm


class InputWidget(Protocol):
    def handle(
        self,
        form: InputForm,
        spec: FieldSpec,
        intent: InputIntent,
        payload: str = "",
        *,
        shift: bool = False,
    ) -> None:
        ...

    def render_row(
        self,
        form: InputForm,
        spec: FieldSpec,
        *,
        active: bool,
        prefix: str,
        label: str,
        value_width: int,
    ) -> Lines:
        ...

    def render_chip(self, form: InputForm, spec: FieldSpec, *, active: bool) -> FormattedText:
        ...


def _selection_range(buf: Buffer) -> tuple[int, int] | None:
    if buf.selection_state is None:
        return None
    return buf.document.selection_range()


def _paint_text_segment(
    text: str,
    *,
    cursor: int | None,
    selection: tuple[int, int] | None,
    show_styles: bool,
) -> FormattedText:
    """Paint one visual line with optional selection + block cursor."""
    n = len(text)
    sel_start = sel_end = -1
    if show_styles and selection is not None:
        a, b = selection
        sel_start, sel_end = (a, b) if a <= b else (b, a)

    def style_at(i: int) -> str:
        if sel_start >= 0 and sel_start <= i < sel_end:
            return "class:form.selection"
        if show_styles and cursor is not None and i == cursor and i < n:
            return "class:form.cursor"
        return "class:form.value"

    out: FormattedText = []
    i = 0
    while i < n:
        st = style_at(i)
        if st == "class:form.cursor":
            out.append((st, text[i]))
            i += 1
            continue
        j = i + 1
        while j < n and style_at(j) == st:
            j += 1
        out.append((st, text[i:j]))
        i = j

    if show_styles and cursor is not None and cursor >= n:
        out.append(("class:form.cursor", " "))
    if not out:
        out.append(("class:form.value", ""))
    return out


def _render_wrapped_text_value(
    buf: Buffer,
    *,
    value_width: int,
    active: bool,
) -> list[FormattedText]:
    text = buf.text
    cursor = buf.cursor_position
    selection = _selection_range(buf) if active else None
    wrap_lines = wrap_text_lines(text, value_width)

    painted: list[FormattedText] = []
    last = len(wrap_lines) - 1
    for line_idx, (start, end) in enumerate(wrap_lines):
        line_text = text[start:end]
        line_cursor: int | None = None
        if active:
            if start <= cursor < end or (cursor == end and line_idx == last):
                line_cursor = cursor - start

        line_sel = None
        if selection is not None:
            sel_start, sel_end = selection
            if sel_end > start and sel_start < end:
                line_sel = (max(0, sel_start - start), min(end - start, sel_end - start))

        painted.append(
            _paint_text_segment(
                line_text,
                cursor=line_cursor,
                selection=line_sel,
                show_styles=active,
            )
        )
    return painted


class TextWidget:
    def handle(
        self,
        form: InputForm,
        spec: FieldSpec,
        intent: InputIntent,
        payload: str = "",
        *,
        shift: bool = False,
    ) -> None:
        if intent == InputIntent.SPACE:
            form.insert_char(" ")
            return
        if intent == InputIntent.SEG_PREV:
            form.move_text_cursor(-1, shift=shift)
        elif intent == InputIntent.SEG_NEXT:
            form.move_text_cursor(1, shift=shift)
        elif intent == InputIntent.WORD_PREV:
            form.move_text_word(-1, shift=shift)
        elif intent == InputIntent.WORD_NEXT:
            form.move_text_word(1, shift=shift)
        elif intent == InputIntent.LINE_HOME:
            form.move_text_line_edge(end=False, shift=shift)
        elif intent == InputIntent.LINE_END:
            form.move_text_line_edge(end=True, shift=shift)
        elif intent == InputIntent.BACKSPACE:
            form.delete_back()
        elif intent == InputIntent.PASTE and payload:
            form.paste_text(payload)
        elif intent == InputIntent.CHAR and payload and payload.isprintable():
            form.insert_char(payload)
        elif intent == InputIntent.INC:
            form.insert_char(payload or "+")
        elif intent == InputIntent.DEC:
            form.insert_char("-")

    def render_row(
        self,
        form: InputForm,
        spec: FieldSpec,
        *,
        active: bool,
        prefix: str,
        label: str,
        value_width: int,
    ) -> Lines:
        buf = form.text_buffer(spec.field)
        label_style = "class:form.active" if active else "class:form.dim"
        if buf is None:
            value = form.get_value_str(spec.field)
            return [[("", prefix), (label_style, label), ("class:form.value", value)]]

        cont_indent = " " * len(prefix + label)
        wrapped = _render_wrapped_text_value(buf, value_width=max(1, value_width), active=active)
        lines: Lines = []
        for i, value_segs in enumerate(wrapped):
            row_prefix = prefix if i == 0 else cont_indent
            row_label = label if i == 0 else ""
            lines.append([("", row_prefix), (label_style, row_label), *value_segs])
        return lines

    def render_chip(self, form: InputForm, spec: FieldSpec, *, active: bool) -> FormattedText:
        value = form.get_value_str(spec.field)
        if active:
            return [("class:form.active", f"{spec.label} "), ("class:form.value.active", value)]
        return [("class:form.dim", f"{spec.label} "), ("class:form.value", value)]


class DateWidget:
    def handle(
        self,
        form: InputForm,
        spec: FieldSpec,
        intent: InputIntent,
        payload: str = "",
        *,
        shift: bool = False,
    ) -> None:
        if intent == InputIntent.SPACE:
            form.move_date_segment(1)
            return
        if intent == InputIntent.SEG_PREV:
            form.move_date_segment(-1)
        elif intent == InputIntent.SEG_NEXT:
            form.move_date_segment(1)
        elif intent == InputIntent.BACKSPACE:
            form.clear_date()
        elif intent == InputIntent.INC:
            form.adjust_date_segment(1)
        elif intent == InputIntent.DEC:
            form.adjust_date_segment(-1)
        elif intent == InputIntent.CHAR and payload.isdigit():
            form.insert_date_digit(payload)

    def render_row(
        self,
        form: InputForm,
        spec: FieldSpec,
        *,
        active: bool,
        prefix: str,
        label: str,
        value_width: int,
    ) -> Lines:
        value = form.get_date_display(spec.field)
        parts = [value[0:4], value[5:7], value[8:10]] if len(value) == 10 else ["____", "__", "__"]
        line: FormattedText = [
            ("", prefix),
            ("class:form.active", label) if active else ("class:form.dim", label),
        ]
        seg = form.date_segment
        for i, part in enumerate(parts):
            if i > 0:
                line.append(("class:form.value", "-"))
            if active and i == seg:
                line.append(("class:form.cursor", part))
            else:
                line.append(("class:form.value", part))
        return [line]

    def render_chip(self, form: InputForm, spec: FieldSpec, *, active: bool) -> FormattedText:
        value = form.get_date_display(spec.field)
        style = "class:form.active" if active else "class:form.dim"
        return [(style, f"{spec.label} "), ("class:form.value", value)]


class StageWidget:
    def handle(
        self,
        form: InputForm,
        spec: FieldSpec,
        intent: InputIntent,
        payload: str = "",
        *,
        shift: bool = False,
    ) -> None:
        if intent == InputIntent.SPACE:
            form.move_stage_segment(1)
            return
        if intent == InputIntent.SEG_PREV:
            form.move_stage_segment(-1)
        elif intent == InputIntent.SEG_NEXT:
            form.move_stage_segment(1)
        elif intent == InputIntent.BACKSPACE:
            form.clear_stage_segment()
        elif intent == InputIntent.INC:
            form.adjust_stage_segment(1)
        elif intent == InputIntent.DEC:
            form.adjust_stage_segment(-1)
        elif intent == InputIntent.CHAR and payload.isdigit():
            form.insert_stage_digit(payload)

    def render_row(
        self,
        form: InputForm,
        spec: FieldSpec,
        *,
        active: bool,
        prefix: str,
        label: str,
        value_width: int,
    ) -> Lines:
        value = form.get_stage_display()
        cur, total = value.split("/", 1) if "/" in value else ("0", "1")
        line: FormattedText = [
            ("", prefix),
            ("class:form.active", label) if active else ("class:form.dim", label),
        ]
        if active and form.stage_segment == 0:
            line.extend([("class:form.cursor", cur), ("class:form.value", "/"), ("class:form.value", total)])
        elif active and form.stage_segment == 1:
            line.extend([("class:form.value", cur), ("class:form.value", "/"), ("class:form.cursor", total)])
        else:
            line.extend([("class:form.value", cur), ("class:form.value", "/"), ("class:form.value", total)])
        return [line]

    def render_chip(self, form: InputForm, spec: FieldSpec, *, active: bool) -> FormattedText:
        style = "class:form.active" if active else "class:form.dim"
        return [(style, f"{spec.label} "), ("class:form.value", form.get_stage_display())]


class HintWidget:
    HINT_BARS = {0: "▁", 1: "▂", 2: "▅", 3: "█"}

    def handle(
        self,
        form: InputForm,
        spec: FieldSpec,
        intent: InputIntent,
        payload: str = "",
        *,
        shift: bool = False,
    ) -> None:
        if intent == InputIntent.SPACE:
            form.adjust_hint(1, wrap=True)
        elif intent == InputIntent.INC:
            form.adjust_hint(1, wrap=False)
        elif intent == InputIntent.DEC:
            form.adjust_hint(-1, wrap=False)

    def render_row(
        self,
        form: InputForm,
        spec: FieldSpec,
        *,
        active: bool,
        prefix: str,
        label: str,
        value_width: int,
    ) -> Lines:
        return [[("", prefix)] + self.render_chip(form, spec, active=active)]

    def render_chip(self, form: InputForm, spec: FieldSpec, *, active: bool) -> FormattedText:
        raw = form.get_value_str(spec.field)
        try:
            n = int(raw)
        except (TypeError, ValueError):
            n = 0
        n = max(0, min(3, n))
        style = "class:form.active" if active else "class:form.dim"
        return [(style, f"{spec.label} "), (f"class:hint.{n}", self.HINT_BARS.get(n, "▁"))]


class SelectWidget:
    def handle(
        self,
        form: InputForm,
        spec: FieldSpec,
        intent: InputIntent,
        payload: str = "",
        *,
        shift: bool = False,
    ) -> None:
        if intent in (InputIntent.SPACE, InputIntent.SEG_NEXT, InputIntent.INC):
            form.cycle_option(1)
        elif intent == InputIntent.DEC:
            form.cycle_option(-1)

    def render_row(
        self,
        form: InputForm,
        spec: FieldSpec,
        *,
        active: bool,
        prefix: str,
        label: str,
        value_width: int,
    ) -> Lines:
        value = form.get_value_str(spec.field)
        if active:
            return [[("", prefix), ("class:form.active", label), ("class:form.value.active", value)]]
        return [[("", prefix), ("class:form.dim", label), ("class:form.value", value)]]

    def render_chip(self, form: InputForm, spec: FieldSpec, *, active: bool) -> FormattedText:
        value = form.get_value_str(spec.field)
        style = "class:form.active" if active else "class:form.dim"
        return [(style, f"{spec.label} "), ("class:form.value", value)]
