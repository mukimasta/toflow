"""Input session model for add/edit workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from toflow.registry import EntityType
from toflow.tui.input.form import InputForm


class InputMode(str, Enum):
    ADD = "add"
    EDIT = "edit"


@dataclass
class InputSession:
    """Holds all state needed for one input interaction."""

    mode: InputMode
    mode_label: str
    entity_type: EntityType
    form: InputForm
    entity_id: int | None = None
    parent_id: int | None = None
    insert_after_id: int | None = None
