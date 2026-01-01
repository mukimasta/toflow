from __future__ import annotations

from typing import Any, Dict

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout import (
    Layout,
    HSplit,
    VSplit,
    Window,
    FormattedTextControl,
    BufferControl,
    ConditionalContainer,
    Dimension,
)

from .states.app_state import AppState, UIMode, View
from .states.input_state import FormField, FormType
from .renderer import Renderer


# ========================================
# Layout Constants
# ========================================

NOW_BOX_WIDTH = 60
NOW_PADDING_LEFT_RIGHT_WEIGHT = 6
NOW_PADDING_TOP_WEIGHT = 45
NOW_PADDING_BOTTOM_WEIGHT = 55

INPUT_PURPOSE_WIDTH = 16
INPUT_TITLE_WIDTH = 28
INPUT_DATE_WIDTH = 10
INPUT_CONTENT_WIDTH = 52


class LayoutManager:
    """
    Owns prompt-toolkit layout construction + buffers required for Input/Command UI.

    Notes:
    - Key bindings remain in app.py and should only mutate state.
    - app.py may call a few helpers here for buffer↔state syncing and focus management.
    """

    def __init__(self, *, state: AppState, renderer: Renderer):
        self._state = state
        self._renderer = renderer

        # == Buffers ==
        self.command_buffer = Buffer()
        self.field_buffers: Dict[FormField, Buffer] = {
            FormField.TITLE: Buffer(),
            FormField.CONTENT: Buffer(),
            FormField.DEADLINE: Buffer(),
            FormField.DATE: Buffer(),
            FormField.START_AT: Buffer(),
        }

        # Focus targets are assigned after layout elements are created
        # prompt-toolkit's focus() accepts a variety of "focusable" values (UIControl/Container/etc).
        # We keep this flexible and let the runtime validate.
        self._focus_targets: dict[FormField, Any] = {}

        # == Conditions (based on state only) ==
        self._is_now_view = Condition(lambda: self._state.view == View.NOW)
        self._is_structure_view = Condition(lambda: self._state.view == View.STRUCTURE)
        self._is_box_view = Condition(lambda: self._state.view == View.BOX)
        self._is_info_view = Condition(lambda: self._state.view == View.INFO)
        self._is_archive_view = Condition(lambda: self._state.view == View.ARCHIVE)
        self._is_timeline_view = Condition(lambda: self._state.view == View.TIMELINE)

        self._is_command_mode = Condition(lambda: self._state.ui_mode == UIMode.COMMAND)
        self._is_input_mode = Condition(lambda: self._state.ui_mode == UIMode.INPUT)

        self._show_deadline = Condition(
            lambda: self._state.input_state.form_type in (FormType.PROJECT, FormType.STRUCTURE_TODO, FormType.BOX_TODO)
        )
        self._show_date = Condition(lambda: self._state.input_state.form_type == FormType.TAKEAWAY)
        self._show_status = Condition(
            lambda: self._state.input_state.form_type
            in (FormType.TRACK, FormType.PROJECT, FormType.STRUCTURE_TODO, FormType.BOX_TODO, FormType.BOX_IDEA)
        )
        self._show_project_hints = Condition(lambda: self._state.input_state.form_type == FormType.PROJECT)
        self._show_takeaway_type = Condition(lambda: self._state.input_state.form_type == FormType.TAKEAWAY)
        self._show_idea_hints = Condition(lambda: self._state.input_state.form_type == FormType.BOX_IDEA)

        self._is_current_title = Condition(lambda: self._state.input_state.current_field == FormField.TITLE)
        self._is_current_deadline = Condition(lambda: self._state.input_state.current_field == FormField.DEADLINE)
        self._is_current_date = Condition(lambda: self._state.input_state.current_field == FormField.DATE)
        self._is_current_content = Condition(lambda: self._state.input_state.current_field == FormField.CONTENT)

    # ==========================================================================
    # Public API
    # ==========================================================================

    def build_layout(self) -> Layout:
        """Build and return the prompt-toolkit Layout."""
        input_form = self._build_input_form()

        layout = Layout(
            HSplit(
                [
                    # ============================================
                    # NOW View (centered main content with padding)
                    # ============================================
                    ConditionalContainer(
                        HSplit(
                            [
                                Window(height=Dimension(weight=NOW_PADDING_TOP_WEIGHT)),
                                VSplit(
                                    [
                                        Window(width=Dimension(weight=NOW_PADDING_LEFT_RIGHT_WEIGHT)),
                                        Window(
                                            content=FormattedTextControl(self._renderer.render_now_view_content),
                                            width=Dimension(preferred=NOW_BOX_WIDTH),
                                            wrap_lines=False,
                                        ),
                                        Window(width=Dimension(weight=NOW_PADDING_LEFT_RIGHT_WEIGHT)),
                                    ]
                                ),
                                Window(height=Dimension(weight=NOW_PADDING_BOTTOM_WEIGHT)),
                            ]
                        ),
                        filter=self._is_now_view,
                    ),
                    # ============================================
                    # STRUCTURE View (full-width main content)
                    # ============================================
                    ConditionalContainer(
                        Window(
                            content=FormattedTextControl(self._renderer.render_structure_view_content),
                            wrap_lines=True,
                        ),
                        filter=self._is_structure_view,
                    ),
                    # ============================================
                    # BOX View (full-width main content)
                    # ============================================
                    ConditionalContainer(
                        Window(
                            content=FormattedTextControl(self._renderer.render_box_view_content),
                            wrap_lines=True,
                        ),
                        filter=self._is_box_view,
                    ),
                    # ============================================
                    # INFO View (full-width main content)
                    # ============================================
                    ConditionalContainer(
                        Window(
                            content=FormattedTextControl(self._renderer.render_info_view_content),
                            wrap_lines=True,
                        ),
                        filter=self._is_info_view,
                    ),
                    # ============================================
                    # ARCHIVE View (full-width main content)
                    # ============================================
                    ConditionalContainer(
                        Window(
                            content=FormattedTextControl(self._renderer.render_archive_view_content),
                            wrap_lines=True,
                        ),
                        filter=self._is_archive_view,
                    ),
                    # ============================================
                    # TIMELINE View (full-width main content)
                    # ============================================
                    ConditionalContainer(
                        Window(
                            content=FormattedTextControl(self._renderer.render_timeline_view_content),
                            wrap_lines=True,
                        ),
                        filter=self._is_timeline_view,
                    ),
                    # ============================================
                    # Separator (shared, full-width)
                    # ============================================
                    Window(height=1, char="─", style="class:separator"),
                    # ============================================
                    # Status Bar (shared, full-width)
                    # ============================================
                    Window(
                        content=FormattedTextControl(self._renderer.render_status_line),
                        height=1,
                    ),
                    # ============================================
                    # Input/Command Mode Area (shared)
                    # ============================================
                    ConditionalContainer(
                        HSplit(
                            [
                                VSplit(
                                    [
                                        Window(content=FormattedTextControl(self._renderer.render_mode_indicator), width=10),
                                        Window(content=FormattedTextControl(self._renderer.render_prompt), width=2),
                                        Window(content=BufferControl(buffer=self.command_buffer)),
                                    ],
                                    height=1,
                                )
                            ]
                        ),
                        filter=self._is_command_mode,
                    ),
                    ConditionalContainer(
                        input_form,
                        filter=self._is_input_mode,
                    ),
                ]
            )
        )
        return layout

    def save_current_text_field_to_state(self) -> None:
        current_field = self._state.input_state.current_field
        if current_field is None:
            return
        if not self._state.input_state.is_text_field(current_field):
            return
        buf = self.field_buffers.get(current_field)
        if buf is None:
            return
        self._state.input_state.set_field_str(current_field, buf.text)

    def sync_all_text_buffers_from_state(self) -> None:
        for field in self.field_buffers.keys():
            if field in self._state.input_state.get_active_fields() and self._state.input_state.is_text_field(field):
                self._load_text_field_from_state(field)

    def reset_buffers(self) -> None:
        for buf in self.field_buffers.values():
            buf.reset()

    def focus_current_field(self, layout: Layout) -> None:
        current_field = self._state.input_state.current_field
        if current_field is None:
            return
        target = self._focus_targets.get(current_field)
        if target is not None:
            layout.focus(target)

    # ==========================================================================
    # Internal helpers
    # ==========================================================================

    def _load_text_field_from_state(self, field: FormField) -> None:
        buf = self.field_buffers.get(field)
        if buf is None:
            return
        value = self._state.input_state.get_field_str(field)
        buf.text = value
        buf.cursor_position = len(buf.text)

    def _build_field_marker_window(self, field: FormField) -> Window:
        return Window(
            content=FormattedTextControl(
                lambda: [("class:selected", "▸")] if self._state.input_state.current_field == field else [("class:dim", " ")]
            ),
            width=1,
            height=1,
        )

    def _build_field_label_window(self, field: FormField, label: str, width: int) -> Window:
        return Window(
            content=FormattedTextControl(
                lambda: [("class:selected", label)] if self._state.input_state.current_field == field else self._renderer.render_input_field_label(label)
            ),
            width=width,
            height=1,
        )

    def _build_text_field_slot(
        self,
        *,
        field: FormField,
        label: str,
        label_width: int,
        edit_window: Window,
        display_window: Window,
        is_current: Condition,
        show: Condition | None = None,
    ):
        slot = VSplit(
            [
                self._build_field_marker_window(field),
                self._build_field_label_window(field, label, label_width),
                ConditionalContainer(edit_window, filter=is_current),
                ConditionalContainer(display_window, filter=~is_current),
            ],
            height=1,
        )
        if show is None:
            return slot
        return ConditionalContainer(slot, filter=show)

    def _build_input_form(self):
        # Text field controls
        title_buffer_control = BufferControl(buffer=self.field_buffers[FormField.TITLE])
        content_buffer_control = BufferControl(buffer=self.field_buffers[FormField.CONTENT])
        deadline_buffer_control = BufferControl(buffer=self.field_buffers[FormField.DEADLINE])
        date_buffer_control = BufferControl(buffer=self.field_buffers[FormField.DATE])

        title_edit_window = Window(
            content=title_buffer_control,
            height=1,
            width=Dimension(preferred=INPUT_TITLE_WIDTH, max=INPUT_TITLE_WIDTH),
            wrap_lines=False,
        )
        title_display_window = Window(
            content=FormattedTextControl(lambda: self._renderer.render_input_text_value(FormField.TITLE)),
            height=1,
            width=Dimension(preferred=INPUT_TITLE_WIDTH, max=INPUT_TITLE_WIDTH),
            wrap_lines=False,
        )

        deadline_edit_window = Window(
            content=deadline_buffer_control,
            height=1,
            width=Dimension(preferred=INPUT_DATE_WIDTH, max=INPUT_DATE_WIDTH),
            wrap_lines=False,
        )
        deadline_display_window = Window(
            content=FormattedTextControl(lambda: self._renderer.render_input_text_value(FormField.DEADLINE)),
            height=1,
            width=Dimension(preferred=INPUT_DATE_WIDTH, max=INPUT_DATE_WIDTH),
            wrap_lines=False,
        )

        date_edit_window = Window(
            content=date_buffer_control,
            height=1,
            width=Dimension(preferred=INPUT_DATE_WIDTH, max=INPUT_DATE_WIDTH),
            wrap_lines=False,
        )
        date_display_window = Window(
            content=FormattedTextControl(lambda: self._renderer.render_input_text_value(FormField.DATE)),
            height=1,
            width=Dimension(preferred=INPUT_DATE_WIDTH, max=INPUT_DATE_WIDTH),
            wrap_lines=False,
        )

        content_edit_window = Window(
            content=content_buffer_control,
            height=1,
            width=Dimension(preferred=INPUT_CONTENT_WIDTH, max=INPUT_CONTENT_WIDTH),
            wrap_lines=False,
        )
        content_display_window = Window(
            content=FormattedTextControl(lambda: self._renderer.render_input_text_value(FormField.CONTENT)),
            height=1,
            width=Dimension(preferred=INPUT_CONTENT_WIDTH, max=INPUT_CONTENT_WIDTH),
            wrap_lines=False,
        )

        # Non-text chip controls
        status_window = Window(
            content=FormattedTextControl(lambda: self._renderer.render_input_chip(FormField.STATUS, "Status")),
            height=1,
            wrap_lines=False,
        )
        type_window = Window(
            content=FormattedTextControl(lambda: self._renderer.render_input_chip(FormField.TYPE, "Type")),
            height=1,
            wrap_lines=False,
        )
        maturity_window = Window(
            content=FormattedTextControl(lambda: self._renderer.render_input_chip(FormField.MATURITY_HINT, "M")),
            height=1,
            wrap_lines=False,
        )
        willingness_window = Window(
            content=FormattedTextControl(lambda: self._renderer.render_input_chip(FormField.WILLINGNESS_HINT, "W")),
            height=1,
            wrap_lines=False,
        )
        importance_window = Window(
            content=FormattedTextControl(lambda: self._renderer.render_input_chip(FormField.IMPORTANCE_HINT, "I")),
            height=1,
            wrap_lines=False,
        )
        urgency_window = Window(
            content=FormattedTextControl(lambda: self._renderer.render_input_chip(FormField.URGENCY_HINT, "U")),
            height=1,
            wrap_lines=False,
        )

        # Focus targets used by app.py keybindings
        self._focus_targets.update(
            {
                FormField.TITLE: title_buffer_control,
                FormField.DEADLINE: deadline_buffer_control,
                FormField.DATE: date_buffer_control,
                FormField.CONTENT: content_buffer_control,
                FormField.STATUS: status_window,
                FormField.TYPE: type_window,
                FormField.MATURITY_HINT: maturity_window,
                FormField.WILLINGNESS_HINT: willingness_window,
                FormField.IMPORTANCE_HINT: importance_window,
                FormField.URGENCY_HINT: urgency_window,
            }
        )

        # == Input Form Line 1 ==
        input_line_1 = VSplit(
            [
                Window(
                    content=FormattedTextControl(self._renderer.render_input_purpose_prompt),
                    height=1,
                    width=Dimension(preferred=INPUT_PURPOSE_WIDTH, max=INPUT_PURPOSE_WIDTH),
                    wrap_lines=False,
                ),
                Window(width=1),
                self._build_text_field_slot(
                    field=FormField.TITLE,
                    label="Title:",
                    label_width=6,
                    edit_window=title_edit_window,
                    display_window=title_display_window,
                    is_current=self._is_current_title,
                ),
                Window(width=1),
                self._build_text_field_slot(
                    field=FormField.DEADLINE,
                    label="DDL:",
                    label_width=4,
                    edit_window=deadline_edit_window,
                    display_window=deadline_display_window,
                    is_current=self._is_current_deadline,
                    show=self._show_deadline,
                ),
                self._build_text_field_slot(
                    field=FormField.DATE,
                    label="Date:",
                    label_width=5,
                    edit_window=date_edit_window,
                    display_window=date_display_window,
                    is_current=self._is_current_date,
                    show=self._show_date,
                ),
            ],
            height=1,
        )

        # == Input Form Line 2 ==
        input_line_2 = VSplit(
            [
                ConditionalContainer(status_window, filter=self._show_status),
                ConditionalContainer(Window(width=1), filter=self._show_status),
                ConditionalContainer(willingness_window, filter=self._show_project_hints),
                ConditionalContainer(Window(width=1), filter=self._show_project_hints),
                ConditionalContainer(importance_window, filter=self._show_project_hints),
                ConditionalContainer(Window(width=1), filter=self._show_project_hints),
                ConditionalContainer(urgency_window, filter=self._show_project_hints),
                ConditionalContainer(Window(width=1), filter=self._show_project_hints),
                ConditionalContainer(maturity_window, filter=self._show_idea_hints),
                ConditionalContainer(Window(width=1), filter=self._show_idea_hints),
                ConditionalContainer(type_window, filter=self._show_takeaway_type),
                ConditionalContainer(Window(width=1), filter=self._show_takeaway_type),
                self._build_text_field_slot(
                    field=FormField.CONTENT,
                    label="Content:",
                    label_width=8,
                    edit_window=content_edit_window,
                    display_window=content_display_window,
                    is_current=self._is_current_content,
                ),
            ],
            height=1,
        )

        return HSplit([input_line_1, input_line_2])


