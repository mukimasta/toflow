"""Form service: build input sessions and submit them."""

from __future__ import annotations

from typing import Any

from toflow.database import db_session
from toflow.ops import Result, create_entity, set_stage, set_status, update_entity
from toflow.registry import EntityType, get_model_class, get_parent_field
from toflow.tui.input.form import InputForm
from toflow.tui.input.session import InputMode, InputSession


class _SubmissionFailed(Exception):
    def __init__(self, result: Result) -> None:
        self.result = result


class FormService:
    """Coordinates form session construction and persistence."""

    def build_add_session(
        self,
        entity_type: EntityType,
        parent_id: int | None = None,
        insert_after_id: int | None = None,
    ) -> InputSession | None:
        fields = self._get_editable_fields(entity_type)
        if not fields:
            return None
        form = InputForm(fields)
        return InputSession(
            mode=InputMode.ADD,
            mode_label="New",
            entity_type=entity_type,
            entity_id=None,
            parent_id=parent_id,
            insert_after_id=insert_after_id,
            form=form,
        )

    def build_edit_session(self, entity_type: EntityType, entity_id: int) -> InputSession | None:
        fields = self._get_editable_fields(entity_type)
        if not fields:
            return None

        with db_session() as s:
            model_cls = get_model_class(entity_type)
            entity = s.get(model_cls, entity_id)
            if entity is None:
                return None
            values = {spec.field: getattr(entity, spec.field, None) for spec in fields}
            if any(spec.widget == "stage" for spec in fields):
                values["current_stage"] = getattr(entity, "current_stage", 0)
                values["total_stages"] = getattr(entity, "total_stages", 1)

        form = InputForm(fields, values)
        return InputSession(
            mode=InputMode.EDIT,
            mode_label="Edit",
            entity_type=entity_type,
            entity_id=entity_id,
            parent_id=None,
            form=form,
        )

    def submit(self, session: InputSession) -> Result:
        if session.mode == InputMode.ADD:
            return self._submit_add(session)
        if session.mode == InputMode.EDIT:
            return self._submit_edit(session)
        return Result(False, None, f"Unsupported input mode: {session.mode}")

    def _submit_add(self, session: InputSession) -> Result:
        form = session.form
        form.sync_text_values()
        values = dict(form.values)
        title = str(values.pop("title", "")).strip()
        if not title:
            return Result(False, None, "Title cannot be empty")

        payload: dict[str, Any] = {"title": title}
        parent_field = get_parent_field(session.entity_type)
        if parent_field is not None and session.parent_id is not None:
            payload[parent_field] = session.parent_id

        stage_payload: tuple[int, int] | None = None
        for spec in form.fields:
            if spec.field == "title":
                continue
            v = values.get(spec.field)
            if spec.widget == "date":
                payload[spec.field] = InputForm.normalize_date_value(v)
                continue
            if spec.widget == "stage":
                cur = int(form.values.get("current_stage", 0) or 0)
                total = int(form.values.get("total_stages", 1) or 1)
                payload["current_stage"] = cur
                payload["total_stages"] = total
                stage_payload = (cur, total)
                continue
            if v is not None and v != "":
                payload[spec.field] = v

        try:
            with db_session() as s:
                created = create_entity(
                    s,
                    session.entity_type,
                    insert_after_id=session.insert_after_id,
                    **payload,
                )
                self._ensure_success(created)

                if (
                    session.entity_type == EntityType.TODO
                    and stage_payload is not None
                    and created.data is not None
                ):
                    cur, total = stage_payload
                    stage_result = set_stage(
                        s,
                        EntityType.TODO,
                        int(created.data),
                        current_stage=cur,
                        total_stages=total,
                    )
                    self._ensure_success(stage_result)

                return created
        except _SubmissionFailed as e:
            return e.result

    def _submit_edit(self, session: InputSession) -> Result:
        if session.entity_id is None:
            return Result(False, None, "Missing entity_id for edit")

        updates = session.form.to_updates()
        if not updates:
            return Result(True, None, "No changes")

        status_update = updates.pop("status", None)
        stage_current = updates.pop("current_stage", None)
        stage_total = updates.pop("total_stages", None)

        try:
            with db_session() as s:
                if updates:
                    result = update_entity(s, session.entity_type, session.entity_id, **updates)
                    self._ensure_success(result)

                if (
                    session.entity_type == EntityType.TODO
                    and (stage_current is not None or stage_total is not None)
                ):
                    model_cls = get_model_class(EntityType.TODO)
                    todo = s.get(model_cls, session.entity_id)
                    if todo is None:
                        raise _SubmissionFailed(Result(False, None, f"todo {session.entity_id} not found"))
                    cur = int(stage_current if stage_current is not None else getattr(todo, "current_stage", 0))
                    total = int(stage_total if stage_total is not None else getattr(todo, "total_stages", 1))
                    stage_result = set_stage(
                        s,
                        EntityType.TODO,
                        session.entity_id,
                        current_stage=cur,
                        total_stages=total,
                    )
                    self._ensure_success(stage_result)

                if status_update is not None:
                    status_result = set_status(
                        s,
                        session.entity_type,
                        session.entity_id,
                        status_update,
                    )
                    self._ensure_success(status_result)

                return Result(True, None, "Saved")
        except _SubmissionFailed as e:
            return e.result

    @staticmethod
    def _ensure_success(result: Result) -> None:
        if not result.success:
            raise _SubmissionFailed(result)

    @staticmethod
    def _get_editable_fields(entity_type: EntityType) -> list:
        model_cls = get_model_class(entity_type)
        instance = model_cls.__new__(model_cls)
        if hasattr(instance, "editable_fields"):
            return instance.editable_fields()
        return []
