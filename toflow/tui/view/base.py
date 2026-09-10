"""View hierarchy — View (ABC with no-op defaults) and EntityView (CRUD for single-entity views)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

from toflow.database import db_session
from toflow.ops import (
    Result,
    delete_entity,
    reorder,
    set_archived,
    set_pinned,
    set_status,
)
from toflow.registry import EntityType, supports_protocol
from toflow.tui.pane.base import Pane

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DBSession

    from toflow.tui.state import AppState


# ---------------------------------------------------------------------------
# View — abstract base with safe no-op defaults
# ---------------------------------------------------------------------------


class View(ABC):
    """Abstract base class for all views.

    All action methods default to None (no-op).  Subclasses override only
    the actions they actually support.  This eliminates boilerplate overrides
    in read-only or modal views.
    """

    title: str = ""
    status_hint: str = ""
    can_add: bool = False
    can_edit: bool = False
    entity_type: EntityType

    @property
    @abstractmethod
    def pane(self) -> Pane:
        """The pane that handles rendering and cursor."""

    def move(self, delta: int) -> None:
        self.pane.move(delta)

    @abstractmethod
    def load_data(self) -> None:
        """Load/reload data from database into the pane."""

    # -- Helper ---------------------------------------------------------------

    def _with_selected(self, op: Callable[[DBSession, dict[str, Any]], Result]) -> Result | None:
        """Get selected item, guard, run op inside db_session, reload, return."""
        item = self.pane.selected_item()
        if not item:
            return None
        with db_session() as s:
            result = op(s, item)
        self.load_data()
        return result

    # -- Navigation -----------------------------------------------------------

    def go_deeper(self, state: AppState) -> None:
        """Right arrow / drill. Default: no-op."""

    def go_back(self, state: AppState) -> None:
        """Left arrow / back. Default: pop one structure level."""
        state.pop_structure()

    def confirm_selection(self, state: AppState) -> None:
        """Enter key. Default: no-op."""

    # -- Actions (all no-op by default) ---------------------------------------

    def delete_selected(self) -> Result | None:
        return None

    def space_action(self) -> Result | None:
        return None

    def sleep_selected(self) -> Result | None:
        return None

    def cancel_selected(self) -> Result | None:
        return None

    def pin_selected(self) -> Result | None:
        return None

    def archive_confirm_action(self) -> Callable[[], Result | None] | None:
        return None

    def reorder_selected(self, direction: int) -> Result | None:
        return None

    # -- Input context --------------------------------------------------------

    def selected_id(self) -> int | None:
        item = self.pane.selected_item()
        if not item:
            return None
        return int(item["id"]) if item.get("id") is not None else None

    def add_entity_type(self) -> EntityType:
        return self.entity_type

    def add_parent_id(self) -> int | None:
        return None

    def add_insert_after_id(self) -> int | None:
        """Sibling id to insert after when adding, or None to append.

        Only returns a selection when the new entity is the same type as the
        view's entity (true sibling). Cross-type adds (e.g. project under a
        selected track) append within the new parent scope.
        """
        if self.add_entity_type() != self.entity_type:
            return None
        if not supports_protocol(self.entity_type, "Orderable"):
            return None
        return self.selected_id()

    def move_context(self):
        return None


# ---------------------------------------------------------------------------
# EntityView — CRUD defaults for single-entity views
# ---------------------------------------------------------------------------


class EntityView(View):
    """View backed by a single entity type with standard CRUD operations.

    Provides delete, toggle, sleep, cancel, pin, archive, reorder out of the
    box.  Subclasses set ``entity_type`` and ``toggle_target`` and get all
    actions for free.
    """

    can_add: bool = True
    can_edit: bool = True
    toggle_target: str = ""

    # -- CRUD actions ---------------------------------------------------------

    def delete_selected(self) -> Result | None:
        return self._with_selected(
            lambda s, item: delete_entity(s, self.entity_type, item["id"])
        )

    def space_action(self) -> Result | None:
        return self.toggle_selected()

    def toggle_selected(self) -> Result | None:
        if not self.toggle_target:
            return None

        def _op(s: DBSession, item: dict[str, Any]) -> Result:
            cur = item.get("status", "active")
            new = "active" if cur == self.toggle_target else self.toggle_target
            return set_status(s, self.entity_type, item["id"], new)

        return self._with_selected(_op)

    def sleep_selected(self) -> Result | None:
        def _op(s: DBSession, item: dict[str, Any]) -> Result:
            cur = item.get("status", "active")
            return set_status(s, self.entity_type, item["id"], "active" if cur == "sleeping" else "sleeping")
        return self._with_selected(_op)

    def cancel_selected(self) -> Result | None:
        def _op(s: DBSession, item: dict[str, Any]) -> Result:
            cur = item.get("status", "active")
            return set_status(s, self.entity_type, item["id"], "active" if cur == "cancelled" else "cancelled")
        return self._with_selected(_op)

    def pin_selected(self) -> Result | None:
        def _op(s: DBSession, item: dict[str, Any]) -> Result:
            return set_pinned(s, self.entity_type, item["id"], pinned=not bool(item.get("pinned")))
        return self._with_selected(_op)

    def archive_confirm_action(self) -> Callable[[], Result | None] | None:
        if not supports_protocol(self.entity_type, "Archivable"):
            return None
        return self._archive_selected

    def _archive_selected(self) -> Result | None:
        return self._with_selected(
            lambda s, item: set_archived(s, self.entity_type, item["id"], archived=True)
        )

    def reorder_selected(self, direction: int) -> Result | None:
        item = self.pane.selected_item()
        if not item:
            return None
        with db_session() as s:
            result = reorder(s, self.entity_type, item["id"], direction)
        self.load_data()
        return result

    # -- Input context --------------------------------------------------------

    def move_context(self):
        if not supports_protocol(self.entity_type, "Parentable"):
            return None
        item = self.pane.selected_item()
        if item is None:
            return None
        from toflow.tui.view.picker import MoveContext
        return MoveContext(
            entity_type=self.entity_type,
            entity_id=item["id"],
            entity_title=item.get("title", "?"),
            current_parent_id=item.get("parent_id"),
        )
