from datetime import datetime, date as date_type, timezone
from sqlalchemy import String, ForeignKey, Date, DateTime, Boolean, Integer, Text, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from mukitodo.database import Base


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (
        CheckConstraint(
            "(archived = false AND archived_at_utc IS NULL) OR (archived = true AND archived_at_utc IS NOT NULL)",
            name="track_archived_consistency"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    archived_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def to_dict(self, local_timezone = None) -> dict:
        '''Convert track to dict. local_timezone: timezone for the time properties'''
        local_timezone = local_timezone or datetime.now().astimezone().tzinfo
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "archived": self.archived,
            "created_at_utc": self.created_at_utc,
            "archived_at_utc": self.archived_at_utc,
            # "created_at_local": self.created_at_utc.astimezone(local_timezone),
            # "archived_at_local": self.archived_at_utc.astimezone(local_timezone) if self.archived_at_utc else None,
            "order_index": self.order_index
        }


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "(archived = false AND archived_at_utc IS NULL) OR (archived = true AND archived_at_utc IS NOT NULL)",
            name="project_archived_consistency"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    willingness_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    importance_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    urgency_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def to_dict(self, local_timezone = None) -> dict:
        '''Convert project to dict. local_timezone: timezone for the time properties'''
        local_timezone = local_timezone or datetime.now().astimezone().tzinfo
        return {
            "id": self.id,
            "track_id": self.track_id,
            "name": self.name,
            "description": self.description,
            "deadline_utc": self.deadline_utc,
            "deadline_local": self.deadline_utc.astimezone(local_timezone) if self.deadline_utc else None,
            "willingness_hint": self.willingness_hint,
            "importance_hint": self.importance_hint,
            "urgency_hint": self.urgency_hint,
            "status": self.status,
            "archived": self.archived,
            "created_at_utc": self.created_at_utc,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "archived_at_utc": self.archived_at_utc,
            # "created_at_local": self.created_at_utc.astimezone(local_timezone),
            # "started_at_local": self.started_at_utc.astimezone(local_timezone) if self.started_at_utc else None,
            # "finished_at_local": self.finished_at_utc.astimezone(local_timezone) if self.finished_at_utc else None,
            # "archived_at_local": self.archived_at_utc.astimezone(local_timezone) if self.archived_at_utc else None,
            "order_index": self.order_index
        }


class TodoItem(Base):
    __tablename__ = "todo_items"
    __table_args__ = (
        CheckConstraint(
            "(archived = false AND archived_at_utc IS NULL) OR (archived = true AND archived_at_utc IS NOT NULL)",
            name="todo_item_archived_consistency"
        ),
        CheckConstraint(
            "(status = 'done' AND completed_at_utc IS NOT NULL) OR (status != 'done' AND completed_at_utc IS NULL)",
            name="todo_item_completed_consistency"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deadline_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def to_dict(self, local_timezone = None) -> dict:
        '''Convert todo item to dict. local_timezone: timezone for the time properties'''
        local_timezone = local_timezone or datetime.now().astimezone().tzinfo
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "deadline_utc": self.deadline_utc,
            "deadline_local": self.deadline_utc.astimezone(local_timezone) if self.deadline_utc else None,
            "status": self.status,
            "archived": self.archived,
            "created_at_utc": self.created_at_utc,
            "completed_at_utc": self.completed_at_utc,
            "archived_at_utc": self.archived_at_utc,
            # "created_at_local": self.created_at_utc.astimezone(local_timezone),
            # "completed_at_local": self.completed_at_utc.astimezone(local_timezone) if self.completed_at_utc else None,
            # "archived_at_local": self.archived_at_utc.astimezone(local_timezone) if self.archived_at_utc else None,
            "order_index": self.order_index
        }


class IdeaItem(Base):
    __tablename__ = "idea_items"
    __table_args__ = (
        CheckConstraint(
            "(archived = false AND archived_at_utc IS NULL) OR (archived = true AND archived_at_utc IS NOT NULL)",
            name="idea_item_archived_consistency"
        ),
        CheckConstraint(
            "(status = 'promoted' AND promoted_at_utc IS NOT NULL) OR (status != 'promoted' AND promoted_at_utc IS NULL AND promoted_to_project_id IS NULL)",
            name="idea_item_promoted_consistency"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    maturity_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    willingness_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    archived_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_to_project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    order_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def to_dict(self, local_timezone = None) -> dict:
        '''Convert idea item to dict. local_timezone: timezone for the time properties'''
        local_timezone = local_timezone or datetime.now().astimezone().tzinfo
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "maturity_hint": self.maturity_hint,
            "willingness_hint": self.willingness_hint,
            "status": self.status,
            "archived": self.archived,
            "created_at_utc": self.created_at_utc,
            "archived_at_utc": self.archived_at_utc,
            "promoted_at_utc": self.promoted_at_utc,
            "promoted_to_project_id": self.promoted_to_project_id,
            # "created_at_local": self.created_at_utc.astimezone(local_timezone),
            # "archived_at_local": self.archived_at_utc.astimezone(local_timezone) if self.archived_at_utc else None,
            # "promoted_at_local": self.promoted_at_utc.astimezone(local_timezone) if self.promoted_at_utc else None,
            "order_index": self.order_index
        }


class NowSession(Base):
    __tablename__ = "now_sessions"
    __table_args__ = (
        CheckConstraint(
            "project_id IS NOT NULL OR todo_item_id IS NOT NULL",
            name="now_session_reference_required"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    todo_item_id: Mapped[int | None] = mapped_column(ForeignKey("todo_items.id"), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self, local_timezone = None) -> dict:
        '''Convert now session to dict. local_timezone: timezone for the time properties'''
        local_timezone = local_timezone or datetime.now().astimezone().tzinfo
        return {
            "id": self.id,
            "description": self.description,
            "project_id": self.project_id,
            "todo_item_id": self.todo_item_id,
            "duration_minutes": self.duration_minutes,
            "started_at_utc": self.started_at_utc,
            "ended_at_utc": self.ended_at_utc,
            # "started_at_local": self.started_at_utc.astimezone(local_timezone),
            # "ended_at_local": self.ended_at_utc.astimezone(local_timezone) if self.ended_at_utc else None
        }


class Takeaway(Base):
    __tablename__ = "takeaways"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    track_id: Mapped[int | None] = mapped_column(ForeignKey("tracks.id"), nullable=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    todo_item_id: Mapped[int | None] = mapped_column(ForeignKey("todo_items.id"), nullable=True)
    now_session_id: Mapped[int | None] = mapped_column(ForeignKey("now_sessions.id"), nullable=True)

    def to_dict(self, local_timezone = None) -> dict:
        '''Convert takeaway to dict. local_timezone: timezone for the time properties'''
        local_timezone = local_timezone or datetime.now().astimezone().tzinfo
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "type": self.type,
            "date": self.date,
            "created_at_utc": self.created_at_utc,
            # "created_at_local": self.created_at_utc.astimezone(local_timezone),
            "track_id": self.track_id,
            "project_id": self.project_id,
            "todo_item_id": self.todo_item_id,
            "now_session_id": self.now_session_id
        }