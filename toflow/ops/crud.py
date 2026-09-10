"""CRUD operations - create, update, delete entity."""

from typing import Any

from sqlalchemy.orm import Session as DBSession

from toflow.ops.result import Result
from toflow.registry import (
    EntityType,
    get_child_type,
    get_model_class,
    get_parent_field,
    get_referrers,
    supports_protocol,
)


def _sibling_query(session: DBSession, entity_type: EntityType, parent_id: int | None):
    """Query non-archived siblings in the same parent scope."""
    model_cls = get_model_class(entity_type)
    parent_field = get_parent_field(entity_type)

    q = session.query(model_cls)
    if parent_field is not None:
        if parent_id is not None:
            q = q.filter(getattr(model_cls, parent_field) == parent_id)
        else:
            q = q.filter(getattr(model_cls, parent_field).is_(None))
    if supports_protocol(entity_type, "Archivable"):
        q = q.filter(getattr(model_cls, "archived_at_utc").is_(None))
    return q.order_by(getattr(model_cls, "order_index").asc().nulls_last(), model_cls.id)


def next_order_index(session: DBSession, entity_type: EntityType, parent_id: int | None) -> int:
    """Compute next order_index for new entity in scope. parent_id=None for Box items (filter by parent_field IS NULL)."""
    items = _sibling_query(session, entity_type, parent_id).all()
    max_idx = -1
    for it in items:
        idx = getattr(it, "order_index", None)
        if idx is not None and idx > max_idx:
            max_idx = idx
    return max_idx + 1


def order_index_after(
    session: DBSession,
    entity_type: EntityType,
    parent_id: int | None,
    after_id: int | None,
) -> int:
    """Return order_index for a new sibling inserted after ``after_id``.

    Shifts later siblings up by one. Falls back to append-at-end when
    ``after_id`` is missing or not a sibling in this scope.
    """
    if after_id is None:
        return next_order_index(session, entity_type, parent_id)

    model_cls = get_model_class(entity_type)
    after = session.get(model_cls, after_id)
    if after is None:
        return next_order_index(session, entity_type, parent_id)

    parent_field = get_parent_field(entity_type)
    if parent_field is not None:
        after_parent = getattr(after, parent_field, None)
        if after_parent != parent_id:
            return next_order_index(session, entity_type, parent_id)

    siblings = _sibling_query(session, entity_type, parent_id).all()
    # Normalize gaps so insert position is stable.
    for idx, it in enumerate(siblings):
        if getattr(it, "order_index", None) != idx:
            it.order_index = idx

    after_idx = None
    for it in siblings:
        if it.id == after_id:
            after_idx = int(it.order_index)
            break
    if after_idx is None:
        return next_order_index(session, entity_type, parent_id)

    for it in siblings:
        idx = int(getattr(it, "order_index", 0) or 0)
        if idx > after_idx:
            it.order_index = idx + 1

    return after_idx + 1


def create_entity(
    session: DBSession,
    entity_type: EntityType,
    *,
    insert_after_id: int | None = None,
    **fields: Any,
) -> Result:
    """Create entity. Result.data: entity id. Handles order_index.

    When ``insert_after_id`` is set (TUI add with selection), the new entity
    is ordered as the next sibling after that id. CLI callers omit it and
    keep append-at-end behavior.
    """
    model_cls = get_model_class(entity_type)

    pf = get_parent_field(entity_type)
    parent_id = fields.get(pf) if pf else None

    if supports_protocol(entity_type, "Orderable"):
        if "order_index" not in fields:
            fields = {
                **fields,
                "order_index": order_index_after(
                    session, entity_type, parent_id, insert_after_id
                ),
            }

    valid_cols = {c.key for c in model_cls.__table__.columns}
    filtered = {k: v for k, v in fields.items() if k in valid_cols}

    if entity_type != EntityType.SESSION:
        if "title" not in filtered or not str(filtered.get("title", "")).strip():
            return Result(False, None, "Title is required")

    entity = model_cls(**filtered)
    session.add(entity)
    session.flush()
    return Result(True, entity.id, f"Created {entity_type.value} {entity.id}")


# Fields that must be changed via dedicated ops (set_status, set_archived, set_pinned, apply_stage_delta)
_PROTECTED_FIELDS = frozenset(
    {"status", "archived_at_utc", "pinned", "finished_at_utc", "current_stage"}
)

def update_entity(session: DBSession, entity_type: EntityType, entity_id: int, **updates: Any) -> Result:
    """Update entity by id. Result.data: None."""
    model_cls = get_model_class(entity_type)
    entity = session.get(model_cls, entity_id)
    if not entity:
        return Result(False, None, f"{entity_type.value} {entity_id} not found")

    for k in updates:
        if k in _PROTECTED_FIELDS:
            return Result(
                False, None, f"Field '{k}' cannot be updated; use the dedicated ops (set_status, set_archived, set_pinned, apply_stage_delta)"
            )

    valid_cols = {c.key for c in model_cls.__table__.columns}
    for k, v in updates.items():
        if k in valid_cols and hasattr(entity, k):
            setattr(entity, k, v)

    display = (getattr(entity, "title", None) or "") or str(entity_id)
    return Result(True, None, f"Updated {entity_type.value} {display}")


def _cascade_delete(session: DBSession, entity_type: EntityType, entity_id: int) -> None:
    """Recursively delete entity and all dependents. Order: referrers -> children -> self."""
    model_cls = get_model_class(entity_type)

    # 1. Delete entities that reference us (must run before we're gone)
    for ref_model, fk_column in get_referrers(entity_type):
        session.query(ref_model).filter(
            getattr(ref_model, fk_column) == entity_id
        ).delete(synchronize_session=False)

    # 2. Recursively delete children (parent_id points to us)
    child_type = get_child_type(entity_type)
    child_parent_field = get_parent_field(child_type) if child_type else None
    if child_type is not None and child_parent_field is not None:
        child_model = get_model_class(child_type)
        children = session.query(child_model).filter(
            getattr(child_model, child_parent_field) == entity_id
        ).all()
        for child in children:
            _cascade_delete(session, child_type, child.id)

    # 3. Delete self
    entity = session.get(model_cls, entity_id)
    if entity is not None:
        session.delete(entity)


def delete_entity(session: DBSession, entity_type: EntityType, entity_id: int) -> Result:
    """Delete entity and cascade. Result.data: deleted entity title."""
    model_cls = get_model_class(entity_type)
    entity = session.get(model_cls, entity_id)
    if not entity:
        return Result(False, None, f"{entity_type.value} {entity_id} not found")

    title = getattr(entity, "title", None) or str(entity_id)
    _cascade_delete(session, entity_type, entity_id)
    return Result(True, title, f"Deleted {entity_type.value} '{title}'")
