from enum import Enum
from typing import Any

from mukitodo import actions
from mukitodo.actions import Result
from datetime import datetime, date as date_type, time as time_type, timezone





class InputPurpose(Enum):
    """Purpose of the input."""
    ADD = "add"
    EDIT = "edit"

class FormType(Enum):
    """Form of the input."""
    TRACK = "track"
    PROJECT = "project"
    STRUCTURE_TODO = "structure_todo"
    BOX_TODO = "box_todo"
    BOX_IDEA = "box_idea"
    # SESSION = "session"
    TAKEAWAY = "takeaway"

class FormField(Enum):
    """Editable field of the input by sequence."""
    # Line 1
    TITLE = ("title", set([FormType.TRACK, FormType.PROJECT, FormType.STRUCTURE_TODO, FormType.BOX_TODO, FormType.BOX_IDEA, FormType.TAKEAWAY])) # name/title
    START_AT = ("start_at", set([FormType.PROJECT]))
    DEADLINE = ("deadline", set([FormType.PROJECT, FormType.STRUCTURE_TODO, FormType.BOX_TODO]))
    DATE = ("date", set([FormType.TAKEAWAY]))
    # Line 2
    TYPE = ("type", set([FormType.TAKEAWAY]))
    STATUS = ("status", set([FormType.TRACK, FormType.PROJECT, FormType.STRUCTURE_TODO, FormType.BOX_TODO, FormType.BOX_IDEA]))
    MATURITY_HINT = ("maturity_hint", set([FormType.BOX_IDEA]))
    WILLINGNESS_HINT = ("willingness_hint", set([FormType.PROJECT, FormType.BOX_IDEA]))
    IMPORTANCE_HINT = ("importance_hint", set([FormType.PROJECT]))
    URGENCY_HINT = ("urgency_hint", set([FormType.PROJECT]))
    CONTENT = ("content", set([FormType.TRACK, FormType.PROJECT, FormType.STRUCTURE_TODO, FormType.BOX_TODO, FormType.BOX_IDEA, FormType.TAKEAWAY])) # content/description/url
    


class InputState:
    """State of the input mode."""
    def __init__(self):
        self._input_purpose: InputPurpose | None = None
        self._form_type: FormType | None = None
        self._current_field: FormField | None = None
        
        self._current_item_id: int | None = None
        self._context_track_id: int | None = None
        self._context_project_id: int | None = None
        self._context_todo_item_id: int | None = None
        self._context_now_session_id: int | None = None

        self._field_dict: dict[FormField, Any] = dict()
        self._original_field_dict: dict[FormField, Any] = dict()
        
    def set_input_context(
        self,
        *,
        input_purpose: InputPurpose,
        form_type: FormType,
        current_item_id: int | None,
        context_track_id: int | None = None,
        context_project_id: int | None = None,
        context_todo_item_id: int | None = None,
        context_now_session_id: int | None = None,
    ) -> None:
        self._input_purpose = input_purpose
        self._form_type = form_type
        self._current_item_id = current_item_id
        self._context_track_id = context_track_id
        self._context_project_id = context_project_id
        self._context_todo_item_id = context_todo_item_id
        self._context_now_session_id = context_now_session_id

        if current_item_id is not None:
            self._load_field_dict(form_type, current_item_id)
        else:
            self._field_dict = dict()
            self._original_field_dict = dict()

        self._ensure_default_field_values()
        active_fields = self.get_active_fields()
        self._current_field = active_fields[0] if active_fields else None

    # == Input Action Management ================================================

    def clear_input_context(self) -> None:
        self._input_purpose = None
        self._form_type = None
        self._current_field = None
        self._current_item_id = None
        self._context_track_id = None
        self._context_project_id = None
        self._context_todo_item_id = None
        self._context_now_session_id = None
        self._field_dict = dict()
        self._original_field_dict = dict()
    

    def confirm_input_action(self) -> Result:
        """Commit the form to actions. Returns Result for status line feedback."""
        if self._input_purpose is None or self._form_type is None:
            return Result(False, None, "Input context is not set")

        if self._input_purpose == InputPurpose.ADD:
            return self._confirm_add()
        else:
            return self._confirm_edit()


    # == Navigation Management ===================================================

    def move_to_next_field(self) -> None:
        fields = self.get_active_fields()
        if not fields:
            return
        if self._current_field not in fields:
            self._current_field = fields[0]
            return
        idx = fields.index(self._current_field)
        self._current_field = fields[(idx + 1) % len(fields)]
        
    def move_to_prev_field(self) -> None:
        fields = self.get_active_fields()
        if not fields:
            return
        if self._current_field not in fields:
            self._current_field = fields[0]
            return
        idx = fields.index(self._current_field)
        self._current_field = fields[(idx - 1) % len(fields)]

    def is_text_input_field(self) -> bool:
        if self._current_field is None:
            return False
        return self.is_text_field(self._current_field)

    # == Field Edit Management ==================================================

    def edit_field_value(self, direction: int | None, value: str | None) -> None:
        """direction: 1 for up/plus, -1 for down/minus, value: new value"""
        if self._current_field is None:
            raise ValueError("Current field is not set")

        # v1: only non-text fields are editable via +/-/Space/Up/Down
        if self.is_text_field(self._current_field):
            return

        if self._current_field == FormField.TYPE:
            current = str(self._field_dict.get(self._current_field) or "action")
            self._field_dict[self._current_field] = self._toggle_takeaway_type(current)
            return

        if self._current_field == FormField.STATUS:
            self._field_dict[self._current_field] = self._cycle_status(direction)
            return

        if self._current_field in (FormField.MATURITY_HINT, FormField.WILLINGNESS_HINT, FormField.IMPORTANCE_HINT, FormField.URGENCY_HINT):
            delta = int(direction or 1)
            self._field_dict[self._current_field] = self._step_hint(self._field_dict.get(self._current_field), delta)
            return

        # Other fields: no-op for now

    # == Field Access ===========================================================

    def set_field_str(self, field: FormField, new_value: str) -> None:
        """Set a field value from a text buffer."""
        if field not in self.get_active_fields():
            return
        if field in (FormField.TITLE, FormField.CONTENT):
            self._field_dict[field] = new_value
        elif field in (FormField.DEADLINE, FormField.DATE, FormField.START_AT):
            self._field_dict[field] = new_value.strip()
        else:
            # Non-text fields should not be set by raw string in v1.
            self._field_dict[field] = new_value

    def get_field_str(self, field: FormField) -> str:
        """String representation for rendering a text field."""
        value = self._field_dict.get(field)
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, datetime):
            return value.astimezone().strftime("%Y-%m-%d")
        if isinstance(value, date_type):
            return value.strftime("%Y-%m-%d")
        return str(value)

    def get_field_display(self, field: FormField) -> str:
        """Compact display string for chips."""
        if field == FormField.STATUS:
            return str(self._field_dict.get(field) or "active")
        if field in (FormField.MATURITY_HINT, FormField.WILLINGNESS_HINT, FormField.IMPORTANCE_HINT, FormField.URGENCY_HINT):
            v = self._field_dict.get(field)
            return str(v) if v is not None else "-"
        if field == FormField.TYPE:
            return str(self._field_dict.get(field) or "action")
        if field in (FormField.DEADLINE, FormField.DATE, FormField.START_AT):
            return self.get_field_str(field) or "-"
        return self.get_field_str(field)

    # == Field Sequence =========================================================

    def get_active_fields(self) -> list[FormField]:
        """Return the ordered fields for current form_type (Tab/Shift+Tab order)."""
        if self._form_type is None:
            return []

        # v1: we only include fields we can actually commit via actions.
        if self._form_type == FormType.TRACK:
            return [FormField.TITLE, FormField.STATUS, FormField.CONTENT]
        if self._form_type == FormType.PROJECT:
            return [
                FormField.TITLE,
                FormField.DEADLINE,
                FormField.STATUS,
                FormField.WILLINGNESS_HINT,
                FormField.IMPORTANCE_HINT,
                FormField.URGENCY_HINT,
                FormField.CONTENT,
            ]
        if self._form_type in (FormType.STRUCTURE_TODO, FormType.BOX_TODO):
            return [FormField.TITLE, FormField.DEADLINE, FormField.STATUS, FormField.CONTENT]
        if self._form_type == FormType.BOX_IDEA:
            return [FormField.TITLE, FormField.STATUS, FormField.MATURITY_HINT, FormField.WILLINGNESS_HINT, FormField.CONTENT]
        if self._form_type == FormType.TAKEAWAY:
            return [FormField.TITLE, FormField.DATE, FormField.TYPE, FormField.CONTENT]
        return []

    def is_text_field(self, field: FormField) -> bool:
        return field in (FormField.TITLE, FormField.CONTENT, FormField.DEADLINE, FormField.DATE, FormField.START_AT)

    @property
    def is_active(self) -> bool:
        return self._input_purpose is not None and self._form_type is not None

    @property
    def input_purpose(self) -> InputPurpose | None:
        return self._input_purpose

    @property
    def form_type(self) -> FormType | None:
        return self._form_type

    @property
    def current_field(self) -> FormField | None:
        return self._current_field

    def set_current_field(self, field: FormField) -> None:
        if field in self.get_active_fields():
            self._current_field = field

    @property
    def context_now_session_id(self) -> int | None:
        return self._context_now_session_id

    @property
    def context_project_id(self) -> int | None:
        return self._context_project_id

    @property
    def context_todo_item_id(self) -> int | None:
        return self._context_todo_item_id

    def reset_for_next_takeaway(self) -> None:
        """Keep takeaway context/type/date, clear title/content, and focus title."""
        if self._form_type != FormType.TAKEAWAY or self._input_purpose != InputPurpose.ADD:
            return

        # Keep TYPE/DATE (user may want to keep them), clear TITLE/CONTENT.
        self._field_dict[FormField.TITLE] = ""
        self._field_dict[FormField.CONTENT] = ""
        self._original_field_dict = dict(self._field_dict)
        self._current_field = FormField.TITLE

    # == Load/Defaults ==========================================================

    def _ensure_default_field_values(self) -> None:
        """Ensure all active fields have initial values."""
        for field in self.get_active_fields():
            if field in self._field_dict:
                continue

            if field == FormField.TITLE:
                self._field_dict[field] = ""
            elif field == FormField.CONTENT:
                self._field_dict[field] = ""
            elif field in (FormField.DEADLINE, FormField.DATE, FormField.START_AT):
                self._field_dict[field] = ""
            elif field == FormField.STATUS:
                self._field_dict[field] = "active"
            elif field == FormField.TYPE:
                self._field_dict[field] = "action"
            elif field in (FormField.MATURITY_HINT, FormField.WILLINGNESS_HINT, FormField.IMPORTANCE_HINT, FormField.URGENCY_HINT):
                self._field_dict[field] = None

    def _load_field_dict(self, form_type: FormType, current_item_id: int) -> None:
        if form_type == FormType.TRACK:
            result = actions.get_track_dict(current_item_id)
            if not result.success:
                raise ValueError(f"[Action Error] Failed to get track dict: {result.message}")
            field_dict = {
                FormField.TITLE: result.data.get("name", ""),
                FormField.STATUS: result.data.get("status", "active"),
                FormField.CONTENT: result.data.get("description") or "",
            }
        elif form_type == FormType.PROJECT:
            result = actions.get_project_dict(current_item_id)
            if not result.success:
                raise ValueError(f"[Action Error] Failed to get project dict: {result.message}")
            deadline_local = result.data.get("deadline_local")
            deadline_str = deadline_local.strftime("%Y-%m-%d") if isinstance(deadline_local, datetime) else ""
            field_dict = {
                FormField.TITLE: result.data.get("name", ""),
                FormField.DEADLINE: deadline_str,
                FormField.STATUS: result.data.get("status", "active"),
                FormField.WILLINGNESS_HINT: result.data.get("willingness_hint"),
                FormField.IMPORTANCE_HINT: result.data.get("importance_hint"),
                FormField.URGENCY_HINT: result.data.get("urgency_hint"),
                FormField.CONTENT: result.data.get("description") or "",
            }
        elif form_type == FormType.STRUCTURE_TODO or form_type == FormType.BOX_TODO:
            result = actions.get_todo_dict(current_item_id)
            if not result.success:
                raise ValueError(f"[Action Error] Failed to get todo dict: {result.message}")
            deadline_local = result.data.get("deadline_local")
            deadline_str = deadline_local.strftime("%Y-%m-%d") if isinstance(deadline_local, datetime) else ""
            field_dict = {
                FormField.TITLE: result.data.get("name", ""),
                FormField.DEADLINE: deadline_str,
                FormField.STATUS: result.data.get("status", "active"),
                FormField.CONTENT: result.data.get("description") or "",
            }
        elif form_type == FormType.BOX_IDEA:
            result = actions.get_idea_item_dict(current_item_id)
            if not result.success:
                raise ValueError(f"[Action Error] Failed to get idea dict: {result.message}")
            field_dict = {
                FormField.TITLE: result.data.get("name", ""),
                FormField.STATUS: result.data.get("status", "active"),
                FormField.MATURITY_HINT: result.data.get("maturity_hint"),
                FormField.WILLINGNESS_HINT: result.data.get("willingness_hint"),
                FormField.CONTENT: result.data.get("description") or "",
            }
        elif form_type == FormType.TAKEAWAY:
            result = actions.get_takeaway_dict(current_item_id)
            if not result.success:
                raise ValueError(f"[Action Error] Failed to get takeaway dict: {result.message}")
            takeaway_date = result.data.get("date")
            date_str = takeaway_date.strftime("%Y-%m-%d") if isinstance(takeaway_date, date_type) else ""
            field_dict = {
                FormField.TITLE: result.data.get("title") or "",
                FormField.TYPE: result.data.get("type") or "action",
                FormField.DATE: date_str,
                FormField.CONTENT: result.data.get("content") or "",
            }
        else:
            raise ValueError(f"Invalid form type: {form_type}")

        self._field_dict = field_dict
        self._original_field_dict = dict(field_dict)


    # == Helper Functions =====================================================

    def _toggle_takeaway_type(self, type: str) -> str:
        """Toggle the takeaway type."""
        if type == "insight":
            return "action"
        elif type == "action":
            return "insight"
        else:
            raise ValueError(f"Invalid takeaway type: {type}")

    def _cycle_status(self, direction: int | None) -> str:
        if self._form_type is None:
            return "active"

        if self._form_type == FormType.TRACK:
            options = ["active", "sleeping"]
        elif self._form_type == FormType.PROJECT:
            options = ["focusing", "active", "sleeping", "finished", "cancelled"]
        elif self._form_type in (FormType.STRUCTURE_TODO, FormType.BOX_TODO):
            options = ["active", "sleeping", "done", "cancelled"]
        elif self._form_type == FormType.BOX_IDEA:
            options = ["active", "sleeping", "deprecated"]
        else:
            options = ["active"]

        current = str(self._field_dict.get(FormField.STATUS) or options[0])
        try:
            idx = options.index(current)
        except ValueError:
            idx = 0
        step = int(direction or 1)
        return options[(idx + step) % len(options)]

    def _step_hint(self, current: Any, delta: int) -> int:
        # v1: hints are 0-3, None means 0 (hidden)
        cur = int(current) if isinstance(current, int) else 0
        nxt = max(0, min(3, cur + delta))
        return nxt

    def _parse_date_yyyy_mm_dd(self, s: str) -> date_type | None:
        s = (s or "").strip()
        if not s:
            return None
        return datetime.strptime(s, "%Y-%m-%d").date()

    def _parse_deadline_datetime_utc(self, s: str) -> datetime | None:
        d = self._parse_date_yyyy_mm_dd(s)
        if d is None:
            return None
        local_tz = datetime.now().astimezone().tzinfo
        dt_local = datetime.combine(d, time_type(0, 0), tzinfo=local_tz)
        return dt_local.astimezone(timezone.utc)

    # == Commit Helpers =========================================================

    def _confirm_add(self) -> Result:
        assert self._form_type is not None

        title = self.get_field_str(FormField.TITLE).strip()
        content = self.get_field_str(FormField.CONTENT).strip()

        created_id: int | None = None
        result: Result

        if self._form_type == FormType.TRACK:
            result = actions.create_track(name=title, description=content or None)
            created_id = result.data if result.success else None

        elif self._form_type == FormType.PROJECT:
            if self._context_track_id is None:
                return Result(False, None, "No track selected for new project")
            deadline = self._parse_deadline_datetime_utc(self.get_field_str(FormField.DEADLINE))
            result = actions.create_project(
                track_id=self._context_track_id,
                name=title,
                description=content or None,
                deadline=deadline,
                willingness_hint=self._field_dict.get(FormField.WILLINGNESS_HINT),
                importance_hint=self._field_dict.get(FormField.IMPORTANCE_HINT),
                urgency_hint=self._field_dict.get(FormField.URGENCY_HINT),
            )
            created_id = result.data if result.success else None

        elif self._form_type == FormType.STRUCTURE_TODO:
            if self._context_project_id is None:
                return Result(False, None, "No project selected for new todo")
            deadline = self._parse_deadline_datetime_utc(self.get_field_str(FormField.DEADLINE))
            result = actions.create_structure_todo(
                project_id=self._context_project_id,
                name=title,
                description=content or None,
                deadline=deadline,
            )
            created_id = result.data if result.success else None

        elif self._form_type == FormType.BOX_TODO:
            deadline = self._parse_deadline_datetime_utc(self.get_field_str(FormField.DEADLINE))
            result = actions.create_box_todo(
                name=title,
                description=content or None,
                deadline=deadline,
            )
            created_id = result.data if result.success else None

        elif self._form_type == FormType.BOX_IDEA:
            result = actions.create_idea_item(
                name=title,
                description=content or None,
                maturity_hint=self._field_dict.get(FormField.MATURITY_HINT),
                willingness_hint=self._field_dict.get(FormField.WILLINGNESS_HINT),
            )
            created_id = result.data if result.success else None

        elif self._form_type == FormType.TAKEAWAY:
            takeaway_type = str(self._field_dict.get(FormField.TYPE) or "action")
            takeaway_date = self._parse_date_yyyy_mm_dd(self.get_field_str(FormField.DATE)) or date_type.today()
            raw_title = self.get_field_str(FormField.TITLE).strip()
            takeaway_title = raw_title or None
            if self._context_todo_item_id is not None:
                result = actions.create_takeaway(
                    title=takeaway_title,
                    content=content,
                    type=takeaway_type,
                    date=takeaway_date,
                    todo_item_id=self._context_todo_item_id,
                    now_session_id=self._context_now_session_id,
                )
            elif self._context_project_id is not None:
                result = actions.create_takeaway(
                    title=takeaway_title,
                    content=content,
                    type=takeaway_type,
                    date=takeaway_date,
                    project_id=self._context_project_id,
                    now_session_id=self._context_now_session_id,
                )
            elif self._context_track_id is not None:
                result = actions.create_takeaway(
                    title=takeaway_title,
                    content=content,
                    type=takeaway_type,
                    date=takeaway_date,
                    track_id=self._context_track_id,
                )
            else:
                return Result(False, None, "No parent selected for new takeaway")
            created_id = result.data if result.success else None

        else:
            return Result(False, None, f"Unsupported form type: {self._form_type.value}")

        if not result.success or created_id is None:
            return result

        # Apply status if user changed it from default on creation.
        status = str(self._field_dict.get(FormField.STATUS) or "active")
        if FormField.STATUS in self.get_active_fields() and status != "active":
            status_result = self._apply_status(form_type=self._form_type, item_id=created_id, status=status)
            if not status_result.success:
                return status_result

        return result

    def _confirm_edit(self) -> Result:
        assert self._form_type is not None
        if self._current_item_id is None:
            return Result(False, None, "No item selected for edit")

        item_id = self._current_item_id
        any_change = False

        def apply(r: Result) -> Result:
            nonlocal any_change
            if not r.success:
                return r
            any_change = True
            return r

        # Title / Content updates
        new_title = self.get_field_str(FormField.TITLE).strip()
        new_content = self.get_field_str(FormField.CONTENT).strip()
        old_title = str(self._original_field_dict.get(FormField.TITLE) or "").strip()
        old_content = str(self._original_field_dict.get(FormField.CONTENT) or "").strip()

        if self._form_type == FormType.TRACK:
            if new_title and new_title != old_title:
                r = apply(actions.rename_track(item_id, new_title))
                if not r.success:
                    return r
            if new_content != old_content:
                r = apply(actions.update_track_description(item_id, new_content))
                if not r.success:
                    return r
            if FormField.STATUS in self.get_active_fields():
                status = str(self._field_dict.get(FormField.STATUS) or "active")
                old_status = str(self._original_field_dict.get(FormField.STATUS) or "active")
                if status != old_status:
                    r = apply(self._apply_status(self._form_type, item_id, status))
                    if not r.success:
                        return r

        elif self._form_type == FormType.PROJECT:
            if new_title and new_title != old_title:
                r = apply(actions.rename_project(item_id, new_title))
                if not r.success:
                    return r
            if new_content != old_content:
                r = apply(actions.update_project_description(item_id, new_content))
                if not r.success:
                    return r
            # deadline
            new_deadline = self.get_field_str(FormField.DEADLINE).strip()
            old_deadline = str(self._original_field_dict.get(FormField.DEADLINE) or "").strip()
            if new_deadline != old_deadline:
                r = apply(actions.update_project_deadline(item_id, self._parse_deadline_datetime_utc(new_deadline)))
                if not r.success:
                    return r
            # hints
            new_w = self._field_dict.get(FormField.WILLINGNESS_HINT)
            new_i = self._field_dict.get(FormField.IMPORTANCE_HINT)
            new_u = self._field_dict.get(FormField.URGENCY_HINT)
            old_w = self._original_field_dict.get(FormField.WILLINGNESS_HINT)
            old_i = self._original_field_dict.get(FormField.IMPORTANCE_HINT)
            old_u = self._original_field_dict.get(FormField.URGENCY_HINT)
            if (new_w, new_i, new_u) != (old_w, old_i, old_u):
                r = apply(actions.update_project_hints(
                    item_id,
                    willingness_hint=new_w,
                    importance_hint=new_i,
                    urgency_hint=new_u,
                ))
                if not r.success:
                    return r
            # status
            status = str(self._field_dict.get(FormField.STATUS) or "active")
            old_status = str(self._original_field_dict.get(FormField.STATUS) or "active")
            if status != old_status:
                r = apply(self._apply_status(self._form_type, item_id, status))
                if not r.success:
                    return r

        elif self._form_type in (FormType.STRUCTURE_TODO, FormType.BOX_TODO):
            if new_title and new_title != old_title:
                r = apply(actions.rename_todo(item_id, new_title))
                if not r.success:
                    return r
            if new_content != old_content:
                r = apply(actions.update_todo_description(item_id, new_content))
                if not r.success:
                    return r
            new_deadline = self.get_field_str(FormField.DEADLINE).strip()
            old_deadline = str(self._original_field_dict.get(FormField.DEADLINE) or "").strip()
            if new_deadline != old_deadline:
                r = apply(actions.update_todo_deadline(item_id, self._parse_deadline_datetime_utc(new_deadline)))
                if not r.success:
                    return r
            status = str(self._field_dict.get(FormField.STATUS) or "active")
            old_status = str(self._original_field_dict.get(FormField.STATUS) or "active")
            if status != old_status:
                r = apply(self._apply_status(self._form_type, item_id, status))
                if not r.success:
                    return r

        elif self._form_type == FormType.BOX_IDEA:
            if new_title and new_title != old_title:
                r = apply(actions.rename_idea_item(item_id, new_title))
                if not r.success:
                    return r
            if new_content != old_content:
                r = apply(actions.update_idea_item_description(item_id, new_content))
                if not r.success:
                    return r
            new_m = self._field_dict.get(FormField.MATURITY_HINT)
            new_w = self._field_dict.get(FormField.WILLINGNESS_HINT)
            old_m = self._original_field_dict.get(FormField.MATURITY_HINT)
            old_w = self._original_field_dict.get(FormField.WILLINGNESS_HINT)
            if (new_m, new_w) != (old_m, old_w):
                r = apply(actions.update_idea_item_hints(
                    item_id,
                    maturity_hint=new_m,
                    willingness_hint=new_w,
                ))
                if not r.success:
                    return r
            status = str(self._field_dict.get(FormField.STATUS) or "active")
            old_status = str(self._original_field_dict.get(FormField.STATUS) or "active")
            if status != old_status:
                r = apply(self._apply_status(self._form_type, item_id, status))
                if not r.success:
                    return r

        elif self._form_type == FormType.TAKEAWAY:
            new_date = self.get_field_str(FormField.DATE).strip()
            old_date = str(self._original_field_dict.get(FormField.DATE) or "").strip()
            if new_title and new_title != old_title:
                r = apply(actions.update_takeaway_title(item_id, new_title))
                if not r.success:
                    return r
            if new_content != old_content:
                r = apply(actions.update_takeaway_content(item_id, new_content))
                if not r.success:
                    return r
            new_type = str(self._field_dict.get(FormField.TYPE) or "action")
            old_type = str(self._original_field_dict.get(FormField.TYPE) or "action")
            if new_type != old_type:
                r = apply(actions.update_takeaway_type(item_id, new_type))
                if not r.success:
                    return r
            if new_date != old_date:
                parsed = self._parse_date_yyyy_mm_dd(new_date)
                if parsed is None:
                    return Result(False, None, "Invalid date format (expected YYYY-MM-DD)")
                r = apply(actions.update_takeaway_date(item_id, parsed))
                if not r.success:
                    return r

        else:
            return Result(False, None, f"Unsupported form type: {self._form_type.value}")

        if not any_change:
            return Result(True, None, "No changes")
        return Result(True, None, "Saved")

    def _apply_status(self, form_type: FormType, item_id: int, status: str) -> Result:
        """Map status string to the corresponding action call."""
        if form_type == FormType.TRACK:
            if status == "active":
                return actions.activate_track(item_id)
            if status == "sleeping":
                return actions.sleep_track(item_id)
            return Result(False, None, f"Unsupported track status: {status}")

        if form_type == FormType.PROJECT:
            if status == "active":
                return actions.activate_project(item_id)
            if status == "focusing":
                return actions.focus_project(item_id)
            if status == "sleeping":
                return actions.sleep_project(item_id)
            if status == "cancelled":
                return actions.cancel_project(item_id)
            if status == "finished":
                return actions.finish_project(item_id)
            return Result(False, None, f"Unsupported project status: {status}")

        if form_type in (FormType.STRUCTURE_TODO, FormType.BOX_TODO):
            if status == "active":
                return actions.activate_todo(item_id)
            if status == "sleeping":
                return actions.sleep_todo(item_id)
            if status == "done":
                return actions.done_todo(item_id)
            if status == "cancelled":
                return actions.cancel_todo(item_id)
            return Result(False, None, f"Unsupported todo status: {status}")

        if form_type == FormType.BOX_IDEA:
            if status == "active":
                return actions.activate_idea_item(item_id)
            if status == "sleeping":
                return actions.sleep_idea_item(item_id)
            if status == "deprecated":
                return actions.deprecate_idea_item(item_id)
            return Result(False, None, f"Unsupported idea status: {status}")

        return Result(True, None, "Status not applicable")