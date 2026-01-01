from dataclasses import dataclass
from datetime import datetime, date as date_type, timezone
from typing import Any

from mukitodo.database import db_session
from mukitodo.models import Track, Project, TodoItem, IdeaItem, NowSession, Takeaway


@dataclass
class Result:
    success: bool | None = None # None only for EmptyResult
    data: Any = None
    message: str = ""

EmptyResult = Result(None, None, "")

def _ensure_tui_meta(d: dict) -> dict:
    """
    Ensure a dict has a dedicated namespace for TUI-only computed fields.

    We keep these under a reserved key to avoid colliding with real model columns.
    """
    if "_tui" not in d or not isinstance(d.get("_tui"), dict):
        d["_tui"] = {}
    return d["_tui"]



# == Status Ordering Helpers ==============================================

def _get_track_status_order():
    """Return SQLAlchemy CASE expression for track status ordering."""
    from sqlalchemy import case
    return case(
        (Track.status == "active", 1),
        (Track.status == "sleeping", 2),
        else_=3
    )

def _get_project_status_order():
    """Return SQLAlchemy CASE expression for project status ordering."""
    from sqlalchemy import case
    return case(
        (Project.status == "focusing", 1),
        (Project.status == "active", 2),
        (Project.status == "sleeping", 3),
        (Project.status == "finished", 4),
        (Project.status == "cancelled", 5),
        else_=6
    )

def _get_todo_status_order():
    """Return SQLAlchemy CASE expression for todo status ordering."""
    from sqlalchemy import case
    return case(
        (TodoItem.status == "active", 1),
        (TodoItem.status == "sleeping", 2),
        (TodoItem.status == "done", 3),
        (TodoItem.status == "cancelled", 4),
        else_=5
    )

def _get_idea_status_order():
    """Return SQLAlchemy CASE expression for idea status ordering."""
    from sqlalchemy import case
    return case(
        (IdeaItem.status == "active", 1),
        (IdeaItem.status == "sleeping", 2),
        (IdeaItem.status == "deprecated", 3),
        (IdeaItem.status == "promoted", 4),
        else_=5
    )


# == Track Actions ========================================================

# Basic CRUD

def create_track(name: str, description: str | None = None) -> Result:
    '''Create a new track. Result.data: track_id. Default status: active'''
    if not name:
        return Result(False, None, "Track name is required")
    
    with db_session() as session:
        track = Track(name=name, description=description)
        session.add(track)
        session.flush()  # Get track.id
        track_id = track.id
        track_name = track.name
    
    return Result(True, track_id, f"Track '{track_name}' created successfully")

def delete_track(track_id: int) -> Result:
    '''Delete a track and all related items (projects, todos, sessions, takeaways). Result.data: (deleted) track.name'''
    with db_session() as session:
        track = session.query(Track).filter_by(id=track_id).first()
        if not track:
            return Result(False, None, f"Track '{track_id}' not found")

        track_name = track.name

        # Get all projects under this track
        projects = session.query(Project).filter_by(track_id=track_id).all()
        project_ids = [p.id for p in projects]

        if project_ids:
            # Delete all todos under these projects
            todos = session.query(TodoItem).filter(TodoItem.project_id.in_(project_ids)).all()
            todo_ids = [t.id for t in todos]

            # Get all session IDs that will be deleted (for deleting related takeaways)
            session_ids_to_delete = []
            if todo_ids:
                todo_session_ids = [s.id for s in session.query(NowSession).filter(NowSession.todo_item_id.in_(todo_ids)).all()]
                session_ids_to_delete.extend(todo_session_ids)
            project_session_ids = [s.id for s in session.query(NowSession).filter(NowSession.project_id.in_(project_ids)).all()]
            session_ids_to_delete.extend(project_session_ids)

            # Delete takeaways related to sessions that will be deleted
            if session_ids_to_delete:
                session.query(Takeaway).filter(Takeaway.now_session_id.in_(session_ids_to_delete)).delete(synchronize_session=False)

            # Delete takeaways related to these todos
            if todo_ids:
                session.query(Takeaway).filter(Takeaway.todo_item_id.in_(todo_ids)).delete(synchronize_session=False)
                # Delete sessions related to these todos
                session.query(NowSession).filter(NowSession.todo_item_id.in_(todo_ids)).delete(synchronize_session=False)

            # Delete takeaways related to these projects
            session.query(Takeaway).filter(Takeaway.project_id.in_(project_ids)).delete(synchronize_session=False)
            # Delete sessions related to these projects
            session.query(NowSession).filter(NowSession.project_id.in_(project_ids)).delete(synchronize_session=False)

            # Delete all todos
            session.query(TodoItem).filter(TodoItem.project_id.in_(project_ids)).delete(synchronize_session=False)

            # Update ideas that were promoted to these projects
            session.query(IdeaItem).filter(IdeaItem.promoted_to_project_id.in_(project_ids)).update(
                {"promoted_to_project_id": None}, synchronize_session=False
            )

            # Delete all projects
            session.query(Project).filter_by(track_id=track_id).delete(synchronize_session=False)

        # Delete takeaways related to this track
        session.query(Takeaway).filter_by(track_id=track_id).delete(synchronize_session=False)

        # Finally delete the track
        session.delete(track)

    return Result(True, track_name, f"Track '{track_name}' and all related items deleted successfully")

def list_tracks_id() -> Result:
    '''List all track ids. Result.data: list of track ids'''
    with db_session() as session:
        tracks = session.query(Track).filter_by(archived=False).all()
        data = [t.id for t in tracks]
    
    return Result(True, data, f"Found {len(tracks)} tracks")

def list_tracks_dict(include_tui_meta: bool = False) -> Result:
    '''List all tracks as dict, sorted by status then by ID. Result.data: list[dict]'''
    with db_session() as session:
        tracks = session.query(Track)\
            .filter_by(archived=False)\
            .order_by(_get_track_status_order(), Track.id)\
            .all()
        data = [t.to_dict() for t in tracks]

        if include_tui_meta and data:
            from sqlalchemy import func

            track_ids = [d["id"] for d in data]
            rows = (
                session.query(Project.track_id, func.count(Project.id))
                .filter(Project.track_id.in_(track_ids), Project.archived == False)  # noqa: E712
                .group_by(Project.track_id)
                .all()
            )
            child_project_count_map = {track_id: int(cnt) for track_id, cnt in rows}

            for d in data:
                meta = _ensure_tui_meta(d)
                meta["child_project_count"] = child_project_count_map.get(d["id"], 0)

    return Result(True, data, f"Found {len(tracks)} tracks")

def get_track_dict(track_id: int) -> Result:
    '''Get a track by id. Result.data: track dict'''
    with db_session() as session:
        track = session.query(Track).filter_by(id=track_id).first()
        
        if not track:
            return Result(False, None, f"Track {track_id} not found")
        
        track_dict = track.to_dict()
        track_name = track.name
    
    return Result(True, track_dict, f"Track '{track_name}' retrieved")

def rename_track(track_id: int, new_name: str) -> Result:
    '''Rename a track. Result.data: (new) track_name'''
    if not new_name:
        return Result(False, None, "Track name is required")
    
    with db_session() as session:
        track = session.query(Track).filter_by(id=track_id).first()
        if not track:
            return Result(False, None, f"Track {track_id} not found")
        
        old_name = track.name
        track.name = new_name
    
    return Result(True, new_name, f"Track renamed from '{old_name}' to '{new_name}'")

def update_track_description(track_id: int, description: str) -> Result:
    '''Update a track's description. Result.data: (new) description'''
    with db_session() as session:
        track = session.query(Track).filter_by(id=track_id).first()
        if not track:
            return Result(False, None, f"Track {track_id} not found")
        
        track_name = track.name
        track.description = description
    
    return Result(True, description, f"Track '{track_name}' description updated")


def activate_track(track_id: int) -> Result:
    '''Activate a track. Result.data: None'''
    with db_session() as session:
        track = session.query(Track).filter_by(id=track_id).first()
        if not track:
            return Result(False, None, f"Track {track_id} not found")
        
        track_name = track.name
        track.status = "active"
    
    return Result(True, None, f"Track '{track_name}' activated")

def sleep_track(track_id: int) -> Result:
    '''Sleep a track. Result.data: None'''
    with db_session() as session:
        track = session.query(Track).filter_by(id=track_id).first()
        if not track:
            return Result(False, None, f"Track {track_id} not found")
        
        track_name = track.name
        track.status = "sleeping"
    
    return Result(True, None, f"Track '{track_name}' set to sleeping")


def archive_track(track_id: int) -> Result:
    '''Archive a track. Result.data: None'''
    with db_session() as session:
        track = session.query(Track).filter_by(id=track_id).first()
        if not track:
            return Result(False, None, f"Track {track_id} not found")
        
        track_name = track.name
        track.archived = True
        track.archived_at_utc = datetime.now(timezone.utc)
    
    return Result(True, None, f"Track '{track_name}' archived")

def unarchive_track(track_id: int) -> Result:
    '''Unarchive a track. Result.data: None'''
    with db_session() as session:
        track = session.query(Track).filter_by(id=track_id).first()
        if not track:
            return Result(False, None, f"Track {track_id} not found")
        
        track_name = track.name
        track.archived = False
        track.archived_at_utc = None
    
    return Result(True, None, f"Track '{track_name}' unarchived")

# def reorder ...




# == Project Actions ========================================================

def create_project(
    track_id: int,
    name: str,
    description: str | None = None,
    deadline: datetime | None = None,
    willingness_hint: int | None = None,
    importance_hint: int | None = None,
    urgency_hint: int | None = None,
    promoted_by_idea_item_id: int | None = None
) -> Result:
    '''Create a new project. Result.data: project_id. Default status: active'''
    if not name:
        return Result(False, None, "Project name is required")
    
    with db_session() as session:
        project = Project(
            track_id=track_id,
            name=name,
            description=description,
            deadline_utc=deadline,
            willingness_hint=willingness_hint,
            importance_hint=importance_hint,
            urgency_hint=urgency_hint
        )
        session.add(project)
        session.flush()  # Get project.id
        
        if promoted_by_idea_item_id:
            idea = session.query(IdeaItem).filter_by(id=promoted_by_idea_item_id).first()
            if idea:
                idea.status = 'promoted'
                idea.promoted_at_utc = datetime.now(timezone.utc)
                idea.promoted_to_project_id = project.id
        
        project_id = project.id
        project_name = project.name
    
    return Result(True, project_id, f"Project '{project_name}' created successfully")

def delete_project(project_id: int) -> Result:
    '''Delete a project and all related items (todos, sessions, takeaways). Result.data: project_name'''
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return Result(False, None, f"Project {project_id} not found")

        project_name = project.name

        # Get all todos under this project
        todos = session.query(TodoItem).filter_by(project_id=project_id).all()
        todo_ids = [t.id for t in todos]

        # Get all session IDs that will be deleted (for deleting related takeaways)
        session_ids_to_delete = []
        if todo_ids:
            todo_session_ids = [s.id for s in session.query(NowSession).filter(NowSession.todo_item_id.in_(todo_ids)).all()]
            session_ids_to_delete.extend(todo_session_ids)
        project_session_ids = [s.id for s in session.query(NowSession).filter_by(project_id=project_id).all()]
        session_ids_to_delete.extend(project_session_ids)

        # Delete takeaways related to sessions that will be deleted
        if session_ids_to_delete:
            session.query(Takeaway).filter(Takeaway.now_session_id.in_(session_ids_to_delete)).delete(synchronize_session=False)

        # Delete takeaways related to todos
        if todo_ids:
            session.query(Takeaway).filter(Takeaway.todo_item_id.in_(todo_ids)).delete(synchronize_session=False)
            # Delete sessions related to todos
            session.query(NowSession).filter(NowSession.todo_item_id.in_(todo_ids)).delete(synchronize_session=False)

        # Delete takeaways related to this project
        session.query(Takeaway).filter_by(project_id=project_id).delete(synchronize_session=False)
        # Delete sessions related to this project
        session.query(NowSession).filter_by(project_id=project_id).delete(synchronize_session=False)

        # Delete all todos
        if todo_ids:
            session.query(TodoItem).filter_by(project_id=project_id).delete(synchronize_session=False)

        # Update ideas that were promoted to this project
        session.query(IdeaItem).filter_by(promoted_to_project_id=project_id).update(
            {"promoted_to_project_id": None}, synchronize_session=False
        )

        # Finally delete the project
        session.delete(project)

    return Result(True, project_name, f"Project '{project_name}' and all related items deleted successfully")

def list_projects_id(track_id: int) -> Result:
    '''List all project ids. Result.data: list of project ids'''
    with db_session() as session:
        projects = session.query(Project).filter_by(track_id=track_id, archived=False).all()
        data = [p.id for p in projects]

    return Result(True, data, f"Found {len(projects)} projects")

def list_projects_dict(track_id: int, include_tui_meta: bool = False) -> Result:
    '''List all projects as dict, sorted by status then by ID. Result.data: list[dict]'''
    with db_session() as session:
        projects = session.query(Project)\
            .filter_by(track_id=track_id, archived=False)\
            .order_by(_get_project_status_order(), Project.id)\
            .all()
        data = [p.to_dict() for p in projects]

        if include_tui_meta and data:
            from sqlalchemy import func

            project_ids = [d["id"] for d in data]

            # --- Child todo count (not displayed yet, but reserved for future) ---
            todo_rows = (
                session.query(TodoItem.project_id, func.count(TodoItem.id))
                .filter(TodoItem.project_id.in_(project_ids), TodoItem.archived == False)  # noqa: E712
                .group_by(TodoItem.project_id)
                .all()
            )
            child_todo_count_map = {pid: int(cnt) for pid, cnt in todo_rows}

            # --- Session count: direct on project + via todos under the project ---
            direct_session_rows = (
                session.query(NowSession.project_id, func.count(NowSession.id))
                .filter(
                    NowSession.project_id.in_(project_ids),
                    NowSession.ended_at_utc.isnot(None),
                )
                .group_by(NowSession.project_id)
                .all()
            )
            direct_session_map = {pid: int(cnt) for pid, cnt in direct_session_rows}

            todo_session_rows = (
                session.query(TodoItem.project_id, func.count(NowSession.id))
                .join(NowSession, NowSession.todo_item_id == TodoItem.id)
                .filter(
                    TodoItem.project_id.in_(project_ids),
                    NowSession.ended_at_utc.isnot(None),
                )
                .group_by(TodoItem.project_id)
                .all()
            )
            todo_session_map = {pid: int(cnt) for pid, cnt in todo_session_rows}

            # --- Takeaway count: direct on project + via todos under the project ---
            direct_takeaway_rows = (
                session.query(Takeaway.project_id, func.count(Takeaway.id))
                .filter(Takeaway.project_id.in_(project_ids))
                .group_by(Takeaway.project_id)
                .all()
            )
            direct_takeaway_map = {pid: int(cnt) for pid, cnt in direct_takeaway_rows}

            todo_takeaway_rows = (
                session.query(TodoItem.project_id, func.count(Takeaway.id))
                .join(Takeaway, Takeaway.todo_item_id == TodoItem.id)
                .filter(TodoItem.project_id.in_(project_ids))
                .group_by(TodoItem.project_id)
                .all()
            )
            todo_takeaway_map = {pid: int(cnt) for pid, cnt in todo_takeaway_rows}

            for d in data:
                pid = d["id"]
                meta = _ensure_tui_meta(d)
                meta["child_todo_count"] = child_todo_count_map.get(pid, 0)
                meta["session_count"] = direct_session_map.get(pid, 0) + todo_session_map.get(pid, 0)
                meta["takeaway_count"] = direct_takeaway_map.get(pid, 0) + todo_takeaway_map.get(pid, 0)

    return Result(True, data, f"Found {len(projects)} projects")

def get_project_dict(project_id: int) -> Result:
    '''Get a project by id. Result.data: project dict'''
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        
        if not project:
            return Result(False, None, f"Project {project_id} not found")
        
        data = project.to_dict()
        project_name = project.name
    
    return Result(True, data, f"Project '{project_name}' retrieved")

def rename_project(project_id: int, new_name: str) -> Result:
    '''Rename a project. Result.data: (new) project_name'''
    if not new_name:
        return Result(False, None, "Project name is required")
    
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return Result(False, None, f"Project {project_id} not found")
        
        old_name = project.name
        project.name = new_name
    
    return Result(True, new_name, f"Project renamed from '{old_name}' to '{new_name}'")

def update_project_description(project_id: int, description: str) -> Result:
    '''Update a project's description. Result.data: (new) description'''
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return Result(False, None, f"Project {project_id} not found")
        
        project_name = project.name
        project.description = description
    
    return Result(True, description, f"Project '{project_name}' description updated")

def update_project_deadline(project_id: int, deadline: datetime | None) -> Result:
    '''Update a project's deadline. Result.data: (new) deadline'''
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return Result(False, None, f"Project {project_id} not found")
        
        project_name = project.name
        project.deadline_utc = deadline
    
    return Result(True, deadline, f"Project '{project_name}' deadline updated")

def update_project_hints(
    project_id: int,
    willingness_hint: int | None = None,
    importance_hint: int | None = None,
    urgency_hint: int | None = None,
) -> Result:
    '''Update a project's hints. Result.data: None'''
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return Result(False, None, f"Project {project_id} not found")
        
        if willingness_hint is not None:
            project.willingness_hint = willingness_hint
        if importance_hint is not None:
            project.importance_hint = importance_hint
        if urgency_hint is not None:
            project.urgency_hint = urgency_hint
        
        project_name = project.name
    
    return Result(True, None, f"Project '{project_name}' hints updated")


def activate_project(project_id: int) -> Result:
    '''Activate a project. Result.data: None'''
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return Result(False, None, f"Project {project_id} not found")
        
        project_name = project.name
        project.status = "active"
    
    return Result(True, None, f"Project '{project_name}' activated")

def focus_project(project_id: int) -> Result:
    '''Focus a project. Result.data: None'''
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return Result(False, None, f"Project {project_id} not found")
        
        project_name = project.name
        project.status = "focusing"
    
    return Result(True, None, f"Project '{project_name}' set to focusing")

def sleep_project(project_id: int) -> Result:
    '''Sleep a project. Result.data: None'''
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return Result(False, None, f"Project {project_id} not found")
        
        project_name = project.name
        project.status = "sleeping"
    
    return Result(True, None, f"Project '{project_name}' set to sleeping")

def cancel_project(project_id: int) -> Result:
    '''Cancel a project. Result.data: None'''
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return Result(False, None, f"Project {project_id} not found")
        
        project_name = project.name
        project.status = "cancelled"
    
    return Result(True, None, f"Project '{project_name}' cancelled")

def finish_project(project_id: int) -> Result:
    '''Finish a project. Result.data: None'''
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return Result(False, None, f"Project {project_id} not found")
        
        project_name = project.name
        project.status = "finished"
    
    return Result(True, None, f"Project '{project_name}' finished")


def archive_project(project_id: int) -> Result:
    '''Archive a project. Result.data: None'''
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return Result(False, None, f"Project {project_id} not found")
        
        project_name = project.name
        project.archived = True
        project.archived_at_utc = datetime.now(timezone.utc)
    
    return Result(True, None, f"Project '{project_name}' archived")

def unarchive_project(project_id: int) -> Result:
    '''Unarchive a project. Result.data: None'''
    with db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return Result(False, None, f"Project {project_id} not found")
        
        project_name = project.name
        project.archived = False
        project.archived_at_utc = None
    
    return Result(True, None, f"Project '{project_name}' unarchived")


# def reorder ...





# == TodoItem Actions - Structure & Box Level =====================================

def create_structure_todo(
    project_id: int,
    name: str,
    description: str | None = None,
    url: str | None = None,
    deadline: datetime | None = None
) -> Result:
    '''Create a new structure todo item. Result.data: todo_item_id. Default status: active'''
    if not name:
        return Result(False, None, "Todo name is required")
    
    with db_session() as session:
        todo = TodoItem(
            project_id=project_id,
            name=name,
            description=description,
            url=url,
            deadline_utc=deadline
        )
        session.add(todo)
        session.flush()  # Get todo.id
        todo_id = todo.id
        todo_name = todo.name
    
    return Result(True, todo_id, f"Todo '{todo_name}' created successfully")



def create_box_todo(
    name: str,
    description: str | None = None,
    url: str | None = None,
    deadline: datetime | None = None
) -> Result:
    '''Create a new box todo item. Result.data: todo_item_id. Default status: active'''
    if not name:
        return Result(False, None, "Todo name is required")
    
    with db_session() as session:
        todo = TodoItem(
            project_id=None,
            name=name,
            description=description,
            url=url,
            deadline_utc=deadline
        )
        session.add(todo)
        session.flush()  # Get todo.id
        todo_id = todo.id
        todo_name = todo.name
    
    return Result(True, todo_id, f"Box todo '{todo_name}' created successfully")



def delete_todo(todo_item_id: int) -> Result:
    '''Delete a todo item and all related items (sessions, takeaways). Result.data: None'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")

        # Get all session IDs related to this todo (for deleting related takeaways)
        session_ids = [s.id for s in session.query(NowSession).filter_by(todo_item_id=todo_item_id).all()]

        # Delete takeaways related to sessions that will be deleted
        if session_ids:
            session.query(Takeaway).filter(Takeaway.now_session_id.in_(session_ids)).delete(synchronize_session=False)

        # Delete takeaways related to this todo
        session.query(Takeaway).filter_by(todo_item_id=todo_item_id).delete(synchronize_session=False)

        # Delete sessions related to this todo
        session.query(NowSession).filter_by(todo_item_id=todo_item_id).delete(synchronize_session=False)

        # Finally delete the todo
        session.delete(todo)

    return Result(True, None, f"Todo and all related items deleted successfully")

def list_structure_todos(project_id: int) -> Result:
    '''List all structure todo items. Result.data: list of todo ids'''
    with db_session() as session:
        todos = session.query(TodoItem).filter_by(project_id=project_id, archived=False).all()
        data = [t.id for t in todos]

    return Result(True, data, f"Found {len(todos)} todos")

def list_structure_todos_dict(project_id: int, include_tui_meta: bool = False) -> Result:
    '''List all structure todo items as dict, sorted by status then by ID. Result.data: list[dict]'''
    with db_session() as session:
        todos = session.query(TodoItem)\
            .filter_by(project_id=project_id, archived=False)\
            .order_by(_get_todo_status_order(), TodoItem.id)\
            .all()
        data = [t.to_dict() for t in todos]

        if include_tui_meta and data:
            from sqlalchemy import func

            todo_ids = [d["id"] for d in data]

            session_rows = (
                session.query(NowSession.todo_item_id, func.count(NowSession.id))
                .filter(
                    NowSession.todo_item_id.in_(todo_ids),
                    NowSession.ended_at_utc.isnot(None),
                )
                .group_by(NowSession.todo_item_id)
                .all()
            )
            session_count_map = {tid: int(cnt) for tid, cnt in session_rows}

            takeaway_rows = (
                session.query(Takeaway.todo_item_id, func.count(Takeaway.id))
                .filter(Takeaway.todo_item_id.in_(todo_ids))
                .group_by(Takeaway.todo_item_id)
                .all()
            )
            takeaway_count_map = {tid: int(cnt) for tid, cnt in takeaway_rows}

            for d in data:
                tid = d["id"]
                meta = _ensure_tui_meta(d)
                meta["session_count"] = session_count_map.get(tid, 0)
                meta["takeaway_count"] = takeaway_count_map.get(tid, 0)

    return Result(True, data, f"Found {len(todos)} todos")

def list_box_todos() -> Result:
    '''List all box todo items. Result.data: list of todo ids'''
    with db_session() as session:
        todos = session.query(TodoItem).filter_by(project_id=None, archived=False).all()
        data = [t.id for t in todos]
    
    return Result(True, data, f"Found {len(todos)} box todos")

def list_box_todos_dict(include_tui_meta: bool = False) -> Result:
    """
    List all box todo items as dict, sorted by status then by ID.
    Box Todo is represented by TodoItem.project_id IS NULL.
    Result.data: list[dict]
    """
    with db_session() as session:
        todos = (
            session.query(TodoItem)
            .filter(TodoItem.project_id.is_(None), TodoItem.archived == False)  # noqa: E712
            .order_by(_get_todo_status_order(), TodoItem.id)
            .all()
        )
        data = [t.to_dict() for t in todos]

        if include_tui_meta and data:
            from sqlalchemy import func

            todo_ids = [d["id"] for d in data]

            session_rows = (
                session.query(NowSession.todo_item_id, func.count(NowSession.id))
                .filter(
                    NowSession.todo_item_id.in_(todo_ids),
                    NowSession.ended_at_utc.isnot(None),
                )
                .group_by(NowSession.todo_item_id)
                .all()
            )
            session_count_map = {tid: int(cnt) for tid, cnt in session_rows}

            takeaway_rows = (
                session.query(Takeaway.todo_item_id, func.count(Takeaway.id))
                .filter(Takeaway.todo_item_id.in_(todo_ids))
                .group_by(Takeaway.todo_item_id)
                .all()
            )
            takeaway_count_map = {tid: int(cnt) for tid, cnt in takeaway_rows}

            for d in data:
                tid = d["id"]
                meta = _ensure_tui_meta(d)
                meta["session_count"] = session_count_map.get(tid, 0)
                meta["takeaway_count"] = takeaway_count_map.get(tid, 0)

    return Result(True, data, f"Found {len(todos)} box todos")

def get_todo_dict(todo_item_id: int) -> Result:
    '''Get a todo item by id. Result.data: todo dict'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")
        
        data = todo.to_dict()
        todo_name = todo.name
    
    return Result(True, data, f"Todo '{todo_name}' retrieved")


def rename_todo(todo_item_id: int, new_name: str) -> Result:
    '''Rename a todo item. Result.data: (new) todo_item_name'''
    if not new_name:
        return Result(False, None, "Todo name is required")
    
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")
        
        old_name = todo.name
        todo.name = new_name
    
    return Result(True, new_name, f"Todo renamed from '{old_name}' to '{new_name}'")

def update_todo_description(todo_item_id: int, description: str) -> Result:
    '''Update a todo item's description. Result.data: (new) description'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")
        
        todo_name = todo.name
        todo.description = description
    
    return Result(True, description, f"Todo '{todo_name}' description updated")

def update_todo_url(todo_item_id: int, url: str) -> Result:
    '''Update a todo item's url. Result.data: (new) url'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")
        
        todo_name = todo.name
        todo.url = url
    
    return Result(True, url, f"Todo '{todo_name}' url updated")

def update_todo_deadline(todo_item_id: int, deadline: datetime | None) -> Result:
    '''Update a todo item's deadline. Result.data: (new) deadline'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")
        
        todo_name = todo.name
        todo.deadline_utc = deadline
    
    return Result(True, deadline, f"Todo '{todo_name}' deadline updated")


def activate_todo(todo_item_id: int) -> Result:
    '''Activate / Undo a todo item. Result.data: None'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")
        
        todo_name = todo.name
        todo.status = "active"
        todo.completed_at_utc = None
    
    return Result(True, None, f"Todo '{todo_name}' activated")

def done_todo(todo_item_id: int) -> Result:
    '''Mark a todo item as done. Result.data: None'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")
        
        todo_name = todo.name
        todo.status = "done"
        todo.completed_at_utc = datetime.now(timezone.utc)
    
    return Result(True, None, f"Todo '{todo_name}' marked as done")


def sleep_todo(todo_item_id: int) -> Result:
    '''Sleep a todo item. Result.data: None'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")

        todo_name = todo.name
        todo.status = "sleeping"
        todo.completed_at_utc = None

    return Result(True, None, f"Todo '{todo_name}' set to sleeping")

def cancel_todo(todo_item_id: int) -> Result:
    '''Cancel a todo item. Result.data: None'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")

        todo_name = todo.name
        todo.status = "cancelled"
        todo.completed_at_utc = None

    return Result(True, None, f"Todo '{todo_name}' cancelled")


def archive_todo(todo_item_id: int) -> Result:
    '''Archive a todo item. Result.data: None'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")
        
        todo_name = todo.name
        todo.archived = True
        todo.archived_at_utc = datetime.now(timezone.utc)
    
    return Result(True, None, f"Todo '{todo_name}' archived")

def unarchive_todo(todo_item_id: int) -> Result:
    '''Unarchive a todo item. Result.data: None'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")
        
        todo_name = todo.name
        todo.archived = False
        todo.archived_at_utc = None
    
    return Result(True, None, f"Todo '{todo_name}' unarchived")


def move_todo_to_project(todo_item_id: int, project_id: int) -> Result:
    '''Move a todo item to a project. Result.data: todo_item_id'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")
        
        todo_name = todo.name
        todo.project_id = project_id
    
    return Result(True, todo_item_id, f"Todo '{todo_name}' moved to project {project_id}")

def move_todo_to_box(todo_item_id: int) -> Result:
    '''Move a todo item to the box. Result.data: todo_item_id'''
    with db_session() as session:
        todo = session.query(TodoItem).filter_by(id=todo_item_id).first()
        if not todo:
            return Result(False, None, f"Todo {todo_item_id} not found")
        
        todo_name = todo.name
        todo.project_id = None
    
    return Result(True, todo_item_id, f"Todo '{todo_name}' moved to box")


# def reorder ...




# == IdeaItem Actions ========================================================

def create_idea_item(
    name: str,
    description: str | None = None,
    maturity_hint: int | None = None,
    willingness_hint: int | None = None,
) -> Result:
    '''Create a new idea item. Result.data: idea_item_id. Default status: active'''
    if not name:
        return Result(False, None, "Idea name is required")
    
    with db_session() as session:
        idea = IdeaItem(
            name=name,
            description=description,
            maturity_hint=maturity_hint,
            willingness_hint=willingness_hint
        )
        session.add(idea)
        session.flush()  # Get idea.id
        idea_id = idea.id
        idea_name = idea.name
    
    return Result(True, idea_id, f"Idea '{idea_name}' created successfully")

def delete_idea_item(idea_item_id: int) -> Result:
    '''Delete an idea item. Result.data: None'''
    with db_session() as session:
        idea = session.query(IdeaItem).filter_by(id=idea_item_id).first()
        if not idea:
            return Result(False, None, f"Idea {idea_item_id} not found")
        
        session.delete(idea)
    
    return Result(True, None, f"Idea deleted successfully")

def list_idea_items() -> Result:
    '''List all idea items. Result.data: list of idea ids'''
    with db_session() as session:
        ideas = session.query(IdeaItem).filter_by(archived=False).all()
        data = [i.id for i in ideas]
    
    return Result(True, data, f"Found {len(ideas)} ideas")

def list_idea_items_dict() -> Result:
    """List all idea items as dict, sorted by status then by ID. Result.data: list[dict]."""
    with db_session() as session:
        ideas = (
            session.query(IdeaItem)
            .filter(IdeaItem.archived == False)  # noqa: E712
            .order_by(_get_idea_status_order(), IdeaItem.id)
            .all()
        )
        data = [i.to_dict() for i in ideas]
    return Result(True, data, f"Found {len(ideas)} ideas")

def get_idea_item_dict(idea_item_id: int) -> Result:
    '''Get an idea item by id. Result.data: idea dict'''
    with db_session() as session:
        idea = session.query(IdeaItem).filter_by(id=idea_item_id).first()
        
        if not idea:
            return Result(False, None, f"Idea {idea_item_id} not found")
        
        data = idea.to_dict()
        idea_name = idea.name
    
    return Result(True, data, f"Idea '{idea_name}' retrieved")


def rename_idea_item(idea_item_id: int, new_name: str) -> Result:
    '''Rename an idea item. Result.data: (new) idea_item_name'''
    if not new_name:
        return Result(False, None, "Idea name is required")
    
    with db_session() as session:
        idea = session.query(IdeaItem).filter_by(id=idea_item_id).first()
        if not idea:
            return Result(False, None, f"Idea {idea_item_id} not found")
        
        old_name = idea.name
        idea.name = new_name
    
    return Result(True, new_name, f"Idea renamed from '{old_name}' to '{new_name}'")

def update_idea_item_description(idea_item_id: int, description: str) -> Result:
    '''Update an idea item's description. Result.data: (new) description'''
    with db_session() as session:
        idea = session.query(IdeaItem).filter_by(id=idea_item_id).first()
        if not idea:
            return Result(False, None, f"Idea {idea_item_id} not found")
        
        idea_name = idea.name
        idea.description = description
    
    return Result(True, description, f"Idea '{idea_name}' description updated")

def update_idea_item_hints(
    idea_item_id: int,
    maturity_hint: int | None = None,
    willingness_hint: int | None = None,
) -> Result:
    '''Update an idea item's hints. Result.data: None'''
    with db_session() as session:
        idea = session.query(IdeaItem).filter_by(id=idea_item_id).first()
        if not idea:
            return Result(False, None, f"Idea {idea_item_id} not found")
        
        if maturity_hint is not None:
            idea.maturity_hint = maturity_hint
        if willingness_hint is not None:
            idea.willingness_hint = willingness_hint
        
        idea_name = idea.name
    
    return Result(True, None, f"Idea '{idea_name}' hints updated")


def activate_idea_item(idea_item_id: int) -> Result:
    '''Activate / Undo an idea item. Result.data: None'''
    with db_session() as session:
        idea = session.query(IdeaItem).filter_by(id=idea_item_id).first()
        if not idea:
            return Result(False, None, f"Idea {idea_item_id} not found")
        
        idea_name = idea.name
        idea.status = "active"
    
    return Result(True, None, f"Idea '{idea_name}' activated")

def sleep_idea_item(idea_item_id: int) -> Result:
    '''Sleep an idea item. Result.data: None'''
    with db_session() as session:
        idea = session.query(IdeaItem).filter_by(id=idea_item_id).first()
        if not idea:
            return Result(False, None, f"Idea {idea_item_id} not found")
        
        idea_name = idea.name
        idea.status = "sleeping"
    
    return Result(True, None, f"Idea '{idea_name}' set to sleeping")

def deprecate_idea_item(idea_item_id: int) -> Result:
    '''Mark an idea item as deprecated. Result.data: None'''
    with db_session() as session:
        idea = session.query(IdeaItem).filter_by(id=idea_item_id).first()
        if not idea:
            return Result(False, None, f"Idea {idea_item_id} not found")
        
        idea_name = idea.name
        idea.status = "deprecated"
    
    return Result(True, None, f"Idea '{idea_name}' marked as deprecated")

def promote_idea_item_to_project(idea_item_id: int, track_id: int) -> Result:
    '''Promote an idea item to a project under a track. Result.data: (new) project_id. Irreversible operation.'''
    with db_session() as session:
        idea = session.query(IdeaItem).filter_by(id=idea_item_id).first()
        if not idea:
            return Result(False, None, f"Idea {idea_item_id} not found")

        # Guard: already promoted ideas cannot be promoted again.
        if idea.status == "promoted" or idea.promoted_to_project_id is not None:
            return Result(False, None, f"Idea '{idea.name}' is already promoted")
        
        # Create project from idea
        project = Project(
            track_id=track_id,
            name=idea.name,
            description=idea.description,
            willingness_hint=idea.willingness_hint,
        )
        session.add(project)
        session.flush()  # Get project.id
        
        # Update idea status
        idea.status = 'promoted'
        idea.promoted_at_utc = datetime.now(timezone.utc)
        idea.promoted_to_project_id = project.id
        
        project_id = project.id
        idea_name = idea.name
    
    return Result(True, project_id, f"Idea '{idea_name}' promoted to project {project_id}")


def archive_idea_item(idea_item_id: int) -> Result:
    '''Archive an idea item. Result.data: None'''
    with db_session() as session:
        idea = session.query(IdeaItem).filter_by(id=idea_item_id).first()
        if not idea:
            return Result(False, None, f"Idea {idea_item_id} not found")
        
        idea_name = idea.name
        idea.archived = True
        idea.archived_at_utc = datetime.now(timezone.utc)
    
    return Result(True, None, f"Idea '{idea_name}' archived")

def unarchive_idea_item(idea_item_id: int) -> Result:
    '''Unarchive an idea item. Result.data: None'''
    with db_session() as session:
        idea = session.query(IdeaItem).filter_by(id=idea_item_id).first()
        if not idea:
            return Result(False, None, f"Idea {idea_item_id} not found")
        
        idea_name = idea.name
        idea.archived = False
        idea.archived_at_utc = None
    
    return Result(True, None, f"Idea '{idea_name}' unarchived")

# def reorder ...



# == Box Actions ========================================================


# == NowSession Actions ========================================================

def save_session(
    project_id: int | None,
    todo_item_id: int | None,
    duration_minutes: int,
    started_at_utc: datetime,
    ended_at_utc: datetime | None = None
) -> Result:
    '''Save a now session. Result.data: now_session_id. Attention: only one of project_id or todo_item_id should be provided.'''
    if project_id is not None and todo_item_id is not None:
        return Result(False, None, "Only one of project_id or todo_item_id should be provided")

    with db_session() as session:
        now_session = NowSession(
            project_id=project_id,
            todo_item_id=todo_item_id,
            duration_minutes=duration_minutes,
            started_at_utc=started_at_utc,
            ended_at_utc=ended_at_utc
        )
        session.add(now_session)
        session.flush()  # Get now_session.id
        now_session_id = now_session.id
    
    return Result(True, now_session_id, f"Session {now_session_id} saved successfully")

def recover_session() -> Result:
    '''Recover a now session. Result.data: session dict'''
    with db_session() as session:
        now_session = session.query(NowSession).filter_by(ended_at_utc=None).first()
        if not now_session:
            return Result(False, None, "No unfinished session found")
        
        data = {
            "id": now_session.id,
            "project_id": now_session.project_id,
            "todo_item_id": now_session.todo_item_id,
            "duration_minutes": now_session.duration_minutes,
            "started_at_utc": now_session.started_at_utc,
            "ended_at_utc": now_session.ended_at_utc
        }
        session_id = now_session.id
    
    return Result(True, data, f"Unfinished session {session_id} recovered")


def delete_session(now_session_id: int) -> Result:
    '''Delete a now session and unlink related takeaways. Result.data: None'''
    with db_session() as session:
        now_session = session.query(NowSession).filter_by(id=now_session_id).first()
        if not now_session:
            return Result(False, None, f"Session {now_session_id} not found")

        # Unlink takeaways from this session (set now_session_id to NULL)
        session.query(Takeaway).filter_by(now_session_id=now_session_id).update(
            {"now_session_id": None}, synchronize_session=False
        )

        # Finally delete the session
        session.delete(now_session)

    return Result(True, None, f"Session deleted successfully")

def list_sessions(track_id: int) -> Result:
    '''List all now sessions. Result.data: list of session ids'''
    with db_session() as session:
        sessions = session.query(NowSession).join(Project).filter(Project.track_id == track_id).all()
        data = [s.id for s in sessions]
    
    return Result(True, data, f"Found {len(sessions)} sessions")

# more list actions in different contexts

def get_session(now_session_id: int) -> Result:
    '''Get a now session by id. Result.data: session dict'''
    with db_session() as session:
        now_session = session.query(NowSession).filter_by(id=now_session_id).first()
        
        if not now_session:
            return Result(False, None, f"Session {now_session_id} not found")
        
        data = now_session.to_dict()
        session_id = now_session.id
    
    return Result(True, data, f"Session {session_id} retrieved")



def link_session_to_takeaway(now_session_id: int, takeaway_id: int) -> Result:
    '''Link a now session to a takeaway. Result.data: None'''
    with db_session() as session:
        now_session = session.query(NowSession).filter_by(id=now_session_id).first()
        if not now_session:
            return Result(False, None, f"Session {now_session_id} not found")
        
        takeaway = session.query(Takeaway).filter_by(id=takeaway_id).first()
        if not takeaway:
            return Result(False, None, f"Takeaway {takeaway_id} not found")
    
    return Result(False, None, "Link session to takeaway: not implemented")







# == Takeaway Actions ========================================================

def create_takeaway(
    title: str | None,
    content: str,
    type: str,
    date: date_type,
    track_id: int | None = None,
    project_id: int | None = None,
    todo_item_id: int | None = None,
    now_session_id: int | None = None
) -> Result:
    '''Create a new takeaway. Result.data: takeaway_id. If title is None, it will be auto generated.
    Attention: only one of track_id, project_id, todo_item_id should be provided.'''

    # only one
    if sum([track_id is not None, project_id is not None, todo_item_id is not None]) != 1:
        return Result(False, None, "Only one of track_id, project_id, todo_item_id, now_session_id should be provided")

    if not content:
        return Result(False, None, "Takeaway content is required")
    
    if not title:
        title = content[:30] + "..." if len(content) > 30 else content
    
    with db_session() as session:
        takeaway = Takeaway(
            title=title,
            content=content,
            type=type,
            date=date,
            track_id=track_id,
            project_id=project_id,
            todo_item_id=todo_item_id,
            now_session_id=now_session_id
        )
        session.add(takeaway)
        session.flush()  # Get takeaway.id
        takeaway_id = takeaway.id
        takeaway_title = takeaway.title
    
    return Result(True, takeaway_id, f"Takeaway '{takeaway_title}' created successfully")


def delete_takeaway(takeaway_id: int) -> Result:
    '''Delete a takeaway. Result.data: None'''
    with db_session() as session:
        takeaway = session.query(Takeaway).filter_by(id=takeaway_id).first()
        if not takeaway:
            return Result(False, None, f"Takeaway {takeaway_id} not found")
        
        session.delete(takeaway)
    
    return Result(True, None, f"Takeaway deleted successfully")

def list_takeaways(track_id: int) -> Result:
    '''List all takeaways. Result.data: list of takeaway ids'''
    with db_session() as session:
        takeaways = session.query(Takeaway).filter_by(track_id=track_id).all()
        data = [t.id for t in takeaways]
    
    return Result(True, data, f"Found {len(takeaways)} takeaways")

# more list actions in different contexts

def get_takeaway_dict(takeaway_id: int) -> Result:
    '''Get a takeaway by id. Result.data: takeaway dict'''
    with db_session() as session:
        takeaway = session.query(Takeaway).filter_by(id=takeaway_id).first()
        
        if not takeaway:
            return Result(False, None, f"Takeaway {takeaway_id} not found")
        
        data = takeaway.to_dict()
        takeaway_title = takeaway.title
    
    return Result(True, data, f"Takeaway '{takeaway_title}' retrieved")

def update_takeaway_type(takeaway_id: int, type: str) -> Result:
    '''Update a takeaway's type. Result.data: (new) type'''
    with db_session() as session:
        takeaway = session.query(Takeaway).filter_by(id=takeaway_id).first()
        if not takeaway:
            return Result(False, None, f"Takeaway {takeaway_id} not found")
        
        takeaway_title = takeaway.title
        takeaway.type = type
    
    return Result(True, type, f"Takeaway '{takeaway_title}' type updated")

def update_takeaway_title(takeaway_id: int, title: str) -> Result:
    '''Update a takeaway's title. Result.data: (new) title'''
    if not title:
        return Result(False, None, "Takeaway title is required")
    
    with db_session() as session:
        takeaway = session.query(Takeaway).filter_by(id=takeaway_id).first()
        if not takeaway:
            return Result(False, None, f"Takeaway {takeaway_id} not found")
        
        takeaway.title = title
    
    return Result(True, title, f"Takeaway title updated")

def update_takeaway_content(takeaway_id: int, content: str) -> Result:
    '''Update a takeaway's content. Result.data: (new) content'''
    if not content:
        return Result(False, None, "Takeaway content is required")
    
    with db_session() as session:
        takeaway = session.query(Takeaway).filter_by(id=takeaway_id).first()
        if not takeaway:
            return Result(False, None, f"Takeaway {takeaway_id} not found")
        
        takeaway_title = takeaway.title
        takeaway.content = content
    
    return Result(True, content, f"Takeaway '{takeaway_title}' content updated")

def update_takeaway_date(takeaway_id: int, date: date_type) -> Result:
    '''Update a takeaway's date. Result.data: (new) date'''
    with db_session() as session:
        takeaway = session.query(Takeaway).filter_by(id=takeaway_id).first()
        if not takeaway:
            return Result(False, None, f"Takeaway {takeaway_id} not found")

        takeaway_title = takeaway.title
        takeaway.date = date

    return Result(True, date, f"Takeaway '{takeaway_title}' date updated")


# == Timeline Actions ========================================================

def list_timeline_records() -> Result:
    '''
    List all Sessions and Takeaways for Timeline View.

    Returns:
        Result.data: list[tuple[dict | None, list[dict]]]
        Each element is (session_dict | None, [takeaway_dict, ...])

        - session_dict is not None and takeaways is not empty: Session with linked Takeaways
        - session_dict is not None and takeaways is empty: Session without Takeaways
        - session_dict is None and takeaways is not empty: Standalone Takeaways (no linked Session)

        Sorted by time descending (session.ended_at_utc or takeaway.created_at_utc for standalone)

        session_dict contains extra field:
        - parent_info: str  # "Track/Project" or "Track/Project/Todo"

        takeaway_dict contains extra field:
        - parent_info: str  # For standalone takeaways only
    '''
    with db_session() as session:
        # Query all NowSessions with ended_at_utc (completed sessions)
        all_sessions = session.query(NowSession)\
            .filter(NowSession.ended_at_utc.isnot(None))\
            .order_by(NowSession.ended_at_utc.desc())\
            .all()

        # Query all Takeaways
        all_takeaways = session.query(Takeaway).all()

        # Build a mapping of session_id -> list of takeaways
        session_takeaways_map: dict[int, list] = {}
        standalone_takeaways: list = []

        for takeaway in all_takeaways:
            if takeaway.now_session_id is not None:
                if takeaway.now_session_id not in session_takeaways_map:
                    session_takeaways_map[takeaway.now_session_id] = []
                session_takeaways_map[takeaway.now_session_id].append(takeaway)
            else:
                standalone_takeaways.append(takeaway)

        # Helper function to build parent_info for session
        def get_session_parent_info(ns: NowSession) -> str:
            parts = []
            if ns.todo_item_id:
                todo = session.query(TodoItem).filter_by(id=ns.todo_item_id).first()
                if todo and todo.project_id:
                    project = session.query(Project).filter_by(id=todo.project_id).first()
                    if project:
                        track = session.query(Track).filter_by(id=project.track_id).first()
                        if track:
                            parts = [track.name, project.name, todo.name]
                        else:
                            parts = [project.name, todo.name]
                else:
                    parts = [todo.name if todo else "Unknown"]
            elif ns.project_id:
                project = session.query(Project).filter_by(id=ns.project_id).first()
                if project:
                    track = session.query(Track).filter_by(id=project.track_id).first()
                    if track:
                        parts = [track.name, project.name]
                    else:
                        parts = [project.name]
            return "/".join(parts) if parts else "Unknown"

        # Helper function to build parent_info for standalone takeaway
        def get_takeaway_parent_info(t: Takeaway) -> str:
            parts = []
            if t.todo_item_id:
                todo = session.query(TodoItem).filter_by(id=t.todo_item_id).first()
                if todo and todo.project_id:
                    project = session.query(Project).filter_by(id=todo.project_id).first()
                    if project:
                        track = session.query(Track).filter_by(id=project.track_id).first()
                        if track:
                            parts = [track.name, project.name, todo.name]
            elif t.project_id:
                project = session.query(Project).filter_by(id=t.project_id).first()
                if project:
                    track = session.query(Track).filter_by(id=project.track_id).first()
                    if track:
                        parts = [track.name, project.name]
            elif t.track_id:
                track = session.query(Track).filter_by(id=t.track_id).first()
                if track:
                    parts = [track.name]
            return "/".join(parts) if parts else "Unknown"

        # Build result list
        result_records: list[tuple[dict | None, list[dict], datetime]] = []

        # Add sessions with their takeaways
        for ns in all_sessions:
            session_dict = ns.to_dict()
            session_dict["parent_info"] = get_session_parent_info(ns)

            takeaways = session_takeaways_map.get(ns.id, [])
            # Sort takeaways by created_at_utc
            takeaways.sort(key=lambda t: t.created_at_utc)
            takeaway_dicts = [t.to_dict() for t in takeaways]

            # Use ended_at_utc for sorting (already filtered for non-None)
            sort_time = ns.ended_at_utc
            if sort_time is not None:
                result_records.append((session_dict, takeaway_dicts, sort_time))

        # Add standalone takeaways
        for t in standalone_takeaways:
            takeaway_dict = t.to_dict()
            takeaway_dict["parent_info"] = get_takeaway_parent_info(t)

            # Use created_at_utc for sorting
            sort_time = t.created_at_utc
            result_records.append((None, [takeaway_dict], sort_time))

        # Sort all records by time descending
        result_records.sort(key=lambda x: x[2], reverse=True)

        # Remove the sort_time from the final result
        final_data = [(rec[0], rec[1]) for rec in result_records]

    session_count = len(all_sessions)
    takeaway_count = len(all_takeaways)
    return Result(True, final_data, f"Found {session_count} sessions and {takeaway_count} takeaways")



# == Archive View ============================================================

def list_archived_structure() -> Result:
    '''
    List all archived items in hierarchical structure for Archive View.

    Returns:
        Result.data: dict with structure:
        {
            "tracks": [
                {
                    "track": track_dict,
                    "is_archived": bool,
                    "projects": [
                        {
                            "project": project_dict,
                            "is_archived": bool,
                            "todos": [todo_dict, ...]
                        }
                    ]
                }
            ],
            "ideas": [idea_dict, ...]
        }
    '''
    with db_session() as session:
        # Query all tracks (including archived)
        all_tracks = session.query(Track).order_by(Track.id).all()

        tracks_with_archived_content = []

        for track in all_tracks:
            track_id = track.id
            track_archived = track.archived

            # Query all projects under this track
            all_projects = session.query(Project)\
                .filter_by(track_id=track_id)\
                .order_by(Project.id)\
                .all()

            projects_with_archived_content = []
            has_archived_content = track_archived

            for project in all_projects:
                project_id = project.id
                project_archived = project.archived

                # Query archived todos under this project
                archived_todos = session.query(TodoItem)\
                    .filter_by(project_id=project_id, archived=True)\
                    .order_by(TodoItem.id)\
                    .all()

                # Include project if: project is archived OR has archived todos
                if project_archived or archived_todos:
                    has_archived_content = True
                    projects_with_archived_content.append({
                        "project": project.to_dict(),
                        "is_archived": project_archived,
                        "todos": [todo.to_dict() for todo in archived_todos]
                    })

            # Only include track if it has archived content
            if has_archived_content:
                tracks_with_archived_content.append({
                    "track": track.to_dict(),
                    "is_archived": track_archived,
                    "projects": projects_with_archived_content
                })

        # Query all archived ideas
        archived_ideas = session.query(IdeaItem)\
            .filter_by(archived=True)\
            .order_by(IdeaItem.id)\
            .all()

        # Query all archived box todos (project_id is NULL)
        archived_box_todos = (
            session.query(TodoItem)
            .filter(TodoItem.project_id.is_(None), TodoItem.archived == True)  # noqa: E712
            .order_by(TodoItem.id)
            .all()
        )

        result_data = {
            "tracks": tracks_with_archived_content,
            "ideas": [idea.to_dict() for idea in archived_ideas],
            "box_todos": [todo.to_dict() for todo in archived_box_todos],
        }

        return Result(
            True,
            result_data,
            f"Found {len(tracks_with_archived_content)} tracks, {len(archived_ideas)} ideas and {len(archived_box_todos)} box todos with archived content",
        )


# == Debugging Functions ======================================================

def set_item_property(item_id: int, item_type: str, field_name: str, value: Any) -> Result:
    '''DO NOT EDIT!! ONLY FOR DEBUGGING: Set a property of an item. Result.data: (new) value'''
    raise ValueError("This function is only for debugging")
    if item_type == "track":
        item_properties_list = get_track_dict(item_id).data.keys()
    elif item_type == "project":
        item_properties_list = get_project_dict(item_id).data.keys()
    elif item_type == "todo":
        item_properties_list = get_todo_dict(item_id).data.keys()
    else:
        raise ValueError(f"Invalid item type: {item_type}")

    if field_name not in item_properties_list:
        return Result(False, None, f"Invalid field name: {field_name}")
    elif field_name == "id":
        return Result(False, None, "Id cannot be changed")

    with db_session() as session:
        if item_type == "track":
            query = session.query(Track)
        elif item_type == "project":
            query = session.query(Project)
        elif item_type == "todo":
            query = session.query(TodoItem)
        else:
            return Result(False, None, f"Invalid item type: {item_type}")
        
        item = query.filter_by(id=item_id).first()
        if not item:
            return Result(False, None, f"Item {item_id} not found")
        
        item_name = getattr(item, "name")
        setattr(item, field_name, value)
    
    return Result(True, value, f"Item '{item_name}': {field_name} set to '{value}'")