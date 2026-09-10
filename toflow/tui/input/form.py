"""InputForm — multi-field form for INPUT mode (add / edit)."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from typing import Any

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.selection import SelectionType

from toflow.models import FieldSpec
from toflow.utils import as_utc_aware
from toflow.tui.input.intent import InputIntent
from toflow.tui.input.widgets import (
    DateWidget,
    HintWidget,
    SelectWidget,
    StageWidget,
    TextWidget,
)


class InputForm:
    """Generic multi-field form driven by FieldSpec list.

    Pure data + cursor logic. No database access.
    Text fields use prompt_toolkit Buffer for editing; other widgets stay custom.
    """

    def __init__(
        self,
        fields: list[FieldSpec],
        values: dict[str, Any] | None = None,
    ) -> None:
        self.fields = fields
        self.values: dict[str, Any] = dict(values) if values else {}

        # Convert datetime values to date strings for date fields (use local time for display)
        for spec in self.fields:
            if spec.widget == "date" and spec.field in self.values:
                v = self.values[spec.field]
                if isinstance(v, datetime):
                    utc = as_utc_aware(v)
                    self.values[spec.field] = utc.astimezone().strftime("%Y-%m-%d") if utc else ""
                elif v is None:
                    self.values[spec.field] = ""

        self.cursor: int = 0
        self._buffers: dict[str, Buffer] = {}
        self.date_segment: int = 0  # 0=year, 1=month, 2=day
        self._date_typing: str = ""  # digit buffer for current segment
        self._date_preview: dict[str, str] = {}  # visible date draft, e.g. "202_-__-__"
        self.stage_segment: int = 0  # 0=current_stage, 1=total_stages
        self._stage_typing: str = ""
        self._widgets = {
            "text": TextWidget(),
            "date": DateWidget(),
            "stage": StageWidget(),
            "hint": HintWidget(),
            "select": SelectWidget(),
            "chip": SelectWidget(),
        }

        # Fill defaults for missing fields
        for spec in self.fields:
            if spec.field not in self.values:
                self.values[spec.field] = self._default_value(spec)
            if spec.widget == "text":
                buf = Buffer(multiline=False)
                buf.text = self.get_value_str(spec.field)
                buf.cursor_position = len(buf.text)
                self._buffers[spec.field] = buf
            if spec.widget == "stage":
                self.values["current_stage"] = self._coerce_int(self.values.get("current_stage"), 0)
                self.values["total_stages"] = max(1, self._coerce_int(self.values.get("total_stages"), 1))
                if self.values["current_stage"] > self.values["total_stages"]:
                    self.values["current_stage"] = self.values["total_stages"]

        self.original: dict[str, Any] = dict(self.values)

        # Init cursor state for first field
        self._sync_field_cursor()

    def _widget_key(self, spec: FieldSpec) -> str:
        if spec.widget in ("chip", "select") and spec.field.endswith("_hint"):
            return "hint"
        return spec.widget

    def _widget(self, spec: FieldSpec):
        return self._widgets.get(self._widget_key(spec), self._widgets["text"])

    def handle_intent(
        self,
        intent: InputIntent,
        payload: str = "",
        *,
        shift: bool = False,
    ) -> None:
        if intent == InputIntent.FIELD_NEXT:
            self.move(1)
            return
        if intent == InputIntent.FIELD_PREV:
            self.move(-1)
            return
        spec = self.current_spec()
        if spec is None:
            return
        self._widget(spec).handle(self, spec, intent, payload, shift=shift)

    def render_row(
        self,
        spec: FieldSpec,
        *,
        active: bool,
        prefix: str,
        label: str,
        value_width: int = 40,
    ):
        return self._widget(spec).render_row(
            self, spec, active=active, prefix=prefix, label=label, value_width=value_width
        )

    def render_chip(self, spec: FieldSpec, *, active: bool):
        return self._widget(spec).render_chip(self, spec, active=active)

    # -- Field cursor --

    def current_spec(self) -> FieldSpec | None:
        if not self.fields:
            return None
        return self.fields[self.cursor]

    def move(self, delta: int) -> None:
        if not self.fields:
            return
        self.cursor = (self.cursor + delta) % len(self.fields)
        self._sync_field_cursor()

    # -- Field type queries --

    def is_text_field(self, spec: FieldSpec | None = None) -> bool:
        spec = spec or self.current_spec()
        if spec is None:
            return False
        return spec.widget == "text"

    def is_date_field(self, spec: FieldSpec | None = None) -> bool:
        spec = spec or self.current_spec()
        if spec is None:
            return False
        return spec.widget == "date"

    def is_hint_field(self, spec: FieldSpec | None = None) -> bool:
        spec = spec or self.current_spec()
        if spec is None:
            return False
        return spec.field.endswith("_hint")

    def is_stage_field(self, spec: FieldSpec | None = None) -> bool:
        spec = spec or self.current_spec()
        if spec is None:
            return False
        return spec.widget == "stage"

    # -- Value access --

    def get_value_str(self, field: str) -> str:
        buf = self._buffers.get(field)
        if buf is not None:
            return buf.text
        v = self.values.get(field)
        if v is None:
            return ""
        return str(v)

    def set_value(self, field: str, value: Any) -> None:
        self.values[field] = value

    # -- Inline text editing (prompt_toolkit Buffer) --

    def active_text_buffer(self) -> Buffer | None:
        spec = self.current_spec()
        if spec is None or not self.is_text_field(spec):
            return None
        return self._buffers.get(spec.field)

    def text_buffer(self, field: str) -> Buffer | None:
        return self._buffers.get(field)

    @property
    def text_cursor(self) -> int:
        buf = self.active_text_buffer()
        return buf.cursor_position if buf is not None else 0

    def sync_text_values(self) -> None:
        """Copy Buffer contents back into values dict."""
        for field, buf in self._buffers.items():
            self.values[field] = buf.text

    def _flush_active_text_buffer(self) -> None:
        spec = self.current_spec()
        if spec is None or not self.is_text_field(spec):
            return
        buf = self._buffers.get(spec.field)
        if buf is not None:
            self.values[spec.field] = buf.text

    @staticmethod
    def _clear_selection(buf: Buffer) -> None:
        if buf.selection_state is not None:
            buf.cut_selection()

    def insert_char(self, char: str) -> None:
        buf = self.active_text_buffer()
        if buf is None:
            return
        self._clear_selection(buf)
        buf.insert_text(char)

    def delete_back(self) -> None:
        buf = self.active_text_buffer()
        if buf is None:
            return
        if buf.selection_state is not None:
            buf.cut_selection()
            return
        if buf.cursor_position > 0:
            buf.delete_before_cursor(count=1)

    def move_text_cursor(self, delta: int, *, shift: bool = False) -> None:
        buf = self.active_text_buffer()
        if buf is None:
            return
        if shift:
            if buf.selection_state is None:
                buf.start_selection(SelectionType.CHARACTERS)
        else:
            buf.exit_selection()
        buf.cursor_position = max(0, min(buf.cursor_position + delta, len(buf.text)))

    def move_text_word(self, delta: int, *, shift: bool = False) -> None:
        buf = self.active_text_buffer()
        if buf is None:
            return
        doc = buf.document
        if delta < 0:
            rel = doc.find_previous_word_beginning(count=1)
            new_pos = 0 if rel is None else buf.cursor_position + rel
        else:
            rel = doc.find_next_word_ending(count=1)
            new_pos = len(buf.text) if rel is None else buf.cursor_position + rel
        if shift:
            if buf.selection_state is None:
                buf.start_selection(SelectionType.CHARACTERS)
        else:
            buf.exit_selection()
        buf.cursor_position = max(0, min(new_pos, len(buf.text)))

    def move_text_line_edge(self, *, end: bool, shift: bool = False) -> None:
        """Move to start (end=False) or end (end=True) of the text field."""
        buf = self.active_text_buffer()
        if buf is None:
            return
        if shift:
            if buf.selection_state is None:
                buf.start_selection(SelectionType.CHARACTERS)
        else:
            buf.exit_selection()
        buf.cursor_position = len(buf.text) if end else 0

    def paste_text(self, text: str) -> None:
        buf = self.active_text_buffer()
        if buf is None or not text:
            return
        cleaned = (
            text.replace("\r\n", " ")
            .replace("\n", " ")
            .replace("\r", " ")
            .replace("\t", " ")
        )
        self._clear_selection(buf)
        buf.insert_text(cleaned)

    def _sync_field_cursor(self) -> None:
        """Reset cursor state when switching fields."""
        self._flush_active_text_buffer()
        spec = self.current_spec()
        if spec and self.is_text_field(spec):
            buf = self._buffers.get(spec.field)
            if buf is not None:
                # Buffer is source of truth for text fields; just place cursor.
                buf.cursor_position = len(buf.text)
                buf.exit_selection()
        self.date_segment = 0
        self._date_typing = ""
        self.stage_segment = 0
        self._stage_typing = ""

    # -- Date segment editing --

    def _parse_date(self) -> tuple[int, int, int]:
        """Parse current date value into (year, month, day)."""
        spec = self.current_spec()
        if spec is None:
            return self._today_parts()
        value = self.get_value_str(spec.field)
        if len(value) == 10:
            try:
                return int(value[0:4]), int(value[5:7]), int(value[8:10])
            except ValueError:
                pass
        return self._today_parts()

    def _set_date(self, year: int, month: int, day: int) -> None:
        """Set date value from parts, clamping to valid range."""
        spec = self.current_spec()
        if spec is None:
            return
        month = max(1, min(12, month))
        max_day = calendar.monthrange(year, month)[1]
        day = max(1, min(max_day, day))
        self.values[spec.field] = f"{year:04d}-{month:02d}-{day:02d}"

    @staticmethod
    def _today_parts() -> tuple[int, int, int]:
        t = date.today()
        return t.year, t.month, t.day

    def move_date_segment(self, delta: int) -> None:
        """Move between year/month/day segments."""
        self._date_typing = ""
        self.date_segment = max(0, min(2, self.date_segment + delta))

    def adjust_date_segment(self, delta: int) -> None:
        """Increment/decrement current date segment by delta."""
        self._date_typing = ""
        spec = self.current_spec()
        if spec is None:
            return
        self._date_preview.pop(spec.field, None)
        value = self.get_value_str(spec.field)
        if not value:
            # Empty date: initialize to today
            y, m, d = self._today_parts()
            self._set_date(y, m, d)
            if delta > 0:
                # Pressing "=" on empty date: jump to day segment
                self.date_segment = 2
            return
        y, m, d = self._parse_date()
        if self.date_segment == 0:
            y += delta
        elif self.date_segment == 1:
            m += delta
            if m > 12:
                m = 1
            elif m < 1:
                m = 12
        else:
            max_day = calendar.monthrange(y, m)[1]
            d += delta
            if d > max_day:
                d = 1
            elif d < 1:
                d = max_day
        self._set_date(y, m, d)

    def insert_date_digit(self, digit: str) -> None:
        """Type a digit into the current date segment."""
        spec = self.current_spec()
        if spec is None:
            return
        field = spec.field
        base = self._date_preview.get(field)
        if base is None:
            value = self.get_value_str(field)
            base = value if len(value) == 10 else "____-__-__"

        seg_bounds = [(0, 4), (5, 7), (8, 10)]
        seg_start, seg_end = seg_bounds[self.date_segment]
        seg_len = seg_end - seg_start

        self._date_typing = (self._date_typing + digit)[-seg_len:]
        typed = self._date_typing.ljust(seg_len, "_")

        preview = base[:seg_start] + typed + base[seg_end:]
        self._date_preview[field] = preview

        # Commit when the date becomes complete and valid.
        if "_" not in preview:
            try:
                y = int(preview[0:4])
                m = int(preview[5:7])
                d = int(preview[8:10])
                self._set_date(y, m, d)
                self._date_preview.pop(field, None)
            except ValueError:
                pass

        # Auto-advance after filling current segment.
        if len(self._date_typing) >= seg_len and self.date_segment < 2:
            self._date_typing = ""
            self.date_segment += 1

    def clear_date(self) -> None:
        """Clear date value (set to empty)."""
        spec = self.current_spec()
        if spec is not None:
            self.values[spec.field] = ""
            self._date_typing = ""
            self.date_segment = 0
            self._date_preview.pop(spec.field, None)

    def get_date_display(self, field: str) -> str:
        """Return display string for date fields, showing in-progress preview."""
        if field in self._date_preview:
            return self._date_preview[field]
        value = self.get_value_str(field)
        if len(value) == 10:
            return value
        return "____-__-__"

    # -- Stage editing (current/total) --

    @staticmethod
    def _coerce_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def move_stage_segment(self, delta: int) -> None:
        self._stage_typing = ""
        self.stage_segment = max(0, min(1, self.stage_segment + delta))

    def adjust_stage_segment(self, delta: int) -> None:
        cur = self._coerce_int(self.values.get("current_stage"), 0)
        total = max(1, self._coerce_int(self.values.get("total_stages"), 1))
        if self.stage_segment == 0:
            cur = max(0, cur + delta)
        else:
            total = max(1, total + delta)
        if cur > total:
            total = cur
        self.values["current_stage"] = cur
        self.values["total_stages"] = total

    def insert_stage_digit(self, digit: str) -> None:
        self._stage_typing = (self._stage_typing + digit)[-4:]
        n = self._coerce_int(self._stage_typing, 0)
        cur = self._coerce_int(self.values.get("current_stage"), 0)
        total = max(1, self._coerce_int(self.values.get("total_stages"), 1))
        if self.stage_segment == 0:
            cur = n
        else:
            total = max(1, n)
        if cur > total:
            total = cur
        self.values["current_stage"] = cur
        self.values["total_stages"] = total

    def clear_stage_segment(self) -> None:
        """Clear active stage segment to its default."""
        if self.stage_segment == 0:
            self.values["current_stage"] = 0
        else:
            self.values["total_stages"] = 1
        cur = self._coerce_int(self.values.get("current_stage"), 0)
        total = max(1, self._coerce_int(self.values.get("total_stages"), 1))
        if cur > total:
            total = cur
            self.values["total_stages"] = total
        self._stage_typing = ""

    def get_stage_display(self) -> str:
        cur = self._coerce_int(self.values.get("current_stage"), 0)
        total = max(1, self._coerce_int(self.values.get("total_stages"), 1))
        return f"{cur}/{total}"

    # -- Chip / select cycling --

    def cycle_option(self, delta: int) -> None:
        """Cycle through options for current chip/select field."""
        spec = self.current_spec()
        if spec is None or not spec.options:
            return
        if self.is_hint_field(spec):
            self.adjust_hint(delta, wrap=False)
            return
        current = self.get_value_str(spec.field)
        try:
            idx = spec.options.index(current)
        except ValueError:
            idx = 0
        new_idx = (idx + delta) % len(spec.options)
        self.values[spec.field] = spec.options[new_idx]

    def adjust_hint(self, delta: int, *, wrap: bool) -> None:
        """Adjust hint value (0..3), optionally wrapping around."""
        spec = self.current_spec()
        if spec is None or not self.is_hint_field(spec):
            return
        try:
            current_num = int(self.get_value_str(spec.field))
        except (TypeError, ValueError):
            current_num = 0
        if wrap:
            current_num = (current_num + delta) % 4
        else:
            current_num = max(0, min(3, current_num + delta))
        self.values[spec.field] = str(current_num)

    # -- Diff --

    def to_updates(self) -> dict[str, Any]:
        """Return only changed fields (vs original). Treats '' and None as equivalent."""
        self.sync_text_values()
        updates: dict[str, Any] = {}
        for spec in self.fields:
            if spec.widget == "stage":
                cur_new = self._coerce_int(self.values.get("current_stage"), 0)
                cur_old = self._coerce_int(self.original.get("current_stage"), 0)
                total_new = max(1, self._coerce_int(self.values.get("total_stages"), 1))
                total_old = max(1, self._coerce_int(self.original.get("total_stages"), 1))
                if cur_new != cur_old:
                    updates["current_stage"] = cur_new
                if total_new != total_old:
                    updates["total_stages"] = total_new
                continue
            new = self.values.get(spec.field)
            old = self.original.get(spec.field)
            new_norm = new if new != "" else None
            old_norm = old if old != "" else None
            if new_norm != old_norm:
                if spec.widget == "date" and new_norm:
                    updates[spec.field] = self.normalize_date_value(new_norm)
                else:
                    updates[spec.field] = new if new != "" else None
        return updates

    @staticmethod
    def normalize_date_value(value: Any) -> datetime | None:
        """Normalize YYYY-MM-DD string-like value to UTC datetime.
        Treats input as local date (midnight local -> UTC)."""
        if value is None or value == "":
            return None
        try:
            dt = datetime.strptime(str(value), "%Y-%m-%d")
            return dt.astimezone(timezone.utc)
        except ValueError:
            return None

    # -- Defaults --

    @staticmethod
    def _default_value(spec: FieldSpec) -> Any:
        if spec.widget == "text":
            return ""
        if spec.widget == "date":
            return ""
        if spec.widget == "stage":
            return 0
        if spec.widget in ("chip", "select") and spec.options:
            return spec.options[0]
        return ""
