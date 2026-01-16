from ast import Not
from datetime import datetime, date as date_type, timezone
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from mukitodo.database import get_session, init_db
from mukitodo.models import Track, Project, TodoItem, IdeaItem, NowSession


# == TrackService ========================================================

class TrackService:
    def __init__(self):
        init_db()
        self.session = get_session()
    
    # == Basic CRUD ==
    
    def get_by_id(self, track_id: int) -> Track | None:
        """Get a track by id. Returns None if not found."""
        return self.session.query(Track).filter_by(id=track_id).first()
    
    def list_all(self, include_archived: bool = True) -> list[Track]:
        """List all tracks. By default filters out archived tracks."""
        query = self.session.query(Track)
        if not include_archived:
            query = query.filter_by(archived=False)
        return query.all()
    
    def add(self, name: str, description: str | None = None) -> Track:
        """Create a new track. Raises DatabaseError on failure."""
        track = Track(name=name, description=description)
        self.session.add(track)
        self.session.commit()
        return track
    
    def delete_by_id(self, track_id: int) -> bool:
        """Delete a track by id. Returns False if not found, raises DatabaseError on constraint violation."""
        track = self.session.query(Track).filter_by(id=track_id).first()
        if not track:
            return False
        self.session.delete(track)
        self.session.commit()
        return True
    
    # == Update Methods ==
    
    def update_name(self, track_id: int, new_name: str) -> bool:
        """Update track name. Returns False if not found."""
        track = self.session.query(Track).filter_by(id=track_id).first()
        if not track:
            return False
        track.name = new_name
        self.session.commit()
        return True
    
    def update_description(self, track_id: int, description: str) -> bool:
        """Update track description. Returns False if not found."""
        track = self.session.query(Track).filter_by(id=track_id).first()
        if not track:
            return False
        track.description = description
        self.session.commit()
        return True
    
    def update_status(self, track_id: int, status: str) -> bool:
        """Update track status. Returns False if not found."""
        track = self.session.query(Track).filter_by(id=track_id).first()
        if not track:
            return False
        track.status = status
        self.session.commit()
        return True
    
    # == Archive Operations ==
    
    def archive(self, track_id: int) -> bool:
        """Archive a track. Returns False if not found."""
        track = self.session.query(Track).filter_by(id=track_id).first()
        if not track:
            return False
        track.archived = True
        track.archived_at_utc = datetime.now(timezone.utc)  # type: ignore
        self.session.commit()
        return True
    
    def unarchive(self, track_id: int) -> bool:
        """Unarchive a track. Returns False if not found."""
        track = self.session.query(Track).filter_by(id=track_id).first()
        if not track:
            return False
        track.archived = False
        track.archived_at_utc = None
        self.session.commit()
        return True


# == ProjectService ========================================================

class ProjectService:
    def __init__(self):
        init_db()
        self.session = get_session()
    
    # == Basic CRUD ==
    
    def get_by_id(self, project_id: int) -> Project | None:
        """Get a project by id. Returns None if not found."""
        return self.session.query(Project).filter_by(id=project_id).first()
    
    def list_by_track_id(self, track_id: int, include_archived: bool = False) -> list[Project]:
        """List all projects in a track. By default filters out archived projects."""
        query = self.session.query(Project).filter_by(track_id=track_id)
        if not include_archived:
            query = query.filter_by(archived=False)
        return query.all()
    
    def add(
        self,
        track_id: int,
        name: str,
        description: str | None = None,
        deadline_utc: datetime | None = None,
        willingness_hint: int | None = None,
        importance_hint: int | None = None,
        urgency_hint: int | None = None
    ) -> Project:
        """Create a new project. Raises DatabaseError on failure."""
        project = Project(
            track_id=track_id,
            name=name,
            description=description,
            deadline_utc=deadline_utc,
            willingness_hint=willingness_hint,
            importance_hint=importance_hint,
            urgency_hint=urgency_hint
        )
        self.session.add(project)
        self.session.commit()
        return project
    
    def delete_by_id(self, project_id: int) -> bool:
        """Delete a project by id. Returns False if not found, raises DatabaseError on constraint violation."""
        project = self.session.query(Project).filter_by(id=project_id).first()
        if not project:
            return False
        self.session.delete(project)
        self.session.commit()
        return True
    
    # == Update Methods ==
    
    def update_name(self, project_id: int, new_name: str) -> bool:
        """Update project name. Returns False if not found."""
        project = self.session.query(Project).filter_by(id=project_id).first()
        if not project:
            return False
        project.name = new_name
        self.session.commit()
        return True
    
    def update_description(self, project_id: int, description: str) -> bool:
        """Update project description. Returns False if not found."""
        project = self.session.query(Project).filter_by(id=project_id).first()
        if not project:
            return False
        project.description = description
        self.session.commit()
        return True
    
    def update_deadline(self, project_id: int, deadline_utc: datetime | None) -> bool:
        """Update project deadline. Returns False if not found."""
        project = self.session.query(Project).filter_by(id=project_id).first()
        if not project:
            return False
        project.deadline_utc = deadline_utc  # type: ignore
        self.session.commit()
        return True
    
    def update_hints(
        self,
        project_id: int,
        willingness_hint: int | None = None,
        importance_hint: int | None = None,
        urgency_hint: int | None = None
    ) -> bool:
        """Update project hints. Returns False if not found."""
        project = self.session.query(Project).filter_by(id=project_id).first()
        if not project:
            return False
        if willingness_hint is not None:
            project.willingness_hint = willingness_hint
        if importance_hint is not None:
            project.importance_hint = importance_hint
        if urgency_hint is not None:
            project.urgency_hint = urgency_hint
        self.session.commit()
        return True
    
    def update_status(self, project_id: int, status: str) -> bool:
        """Update project status. Returns False if not found."""
        project = self.session.query(Project).filter_by(id=project_id).first()
        if not project:
            return False
        project.status = status
        self.session.commit()
        return True
    
    # == Archive Operations ==
    
    def archive(self, project_id: int) -> bool:
        """Archive a project. Returns False if not found."""
        project = self.session.query(Project).filter_by(id=project_id).first()
        if not project:
            return False
        project.archived = True
        project.archived_at_utc = datetime.now(timezone.utc)  # type: ignore
        self.session.commit()
        return True
    
    def unarchive(self, project_id: int) -> bool:
        """Unarchive a project. Returns False if not found."""
        project = self.session.query(Project).filter_by(id=project_id).first()
        if not project:
            return False
        project.archived = False
        project.archived_at_utc = None
        self.session.commit()
        return True


# == TodoItemService ========================================================

class TodoItemService:
    def __init__(self):
        init_db()
        self.session = get_session()
    
    # == Basic CRUD ==
    
    def get_by_id(self, todo_id: int) -> TodoItem | None:
        """Get a todo item by id. Returns None if not found."""
        return self.session.query(TodoItem).filter_by(id=todo_id).first()
    
    def list_by_project_id(self, project_id: int, include_archived: bool = False) -> list[TodoItem]:
        """List all todo items in a project. By default filters out archived items."""
        query = self.session.query(TodoItem).filter_by(project_id=project_id)
        if not include_archived:
            query = query.filter_by(archived=False)
        return query.all()
    
    def list_box_todos(self, include_archived: bool = False) -> list[TodoItem]:
        """List all box todos (project_id is None). By default filters out archived items."""
        query = self.session.query(TodoItem).filter_by(project_id=None)
        if not include_archived:
            query = query.filter_by(archived=False)
        return query.all()
    
    def add(
        self,
        project_id: int | None,
        name: str,
        description: str | None = None,
        url: str | None = None,
        deadline_utc: datetime | None = None
    ) -> TodoItem:
        """Create a new todo item. project_id=None means box todo. Raises DatabaseError on failure."""
        todo = TodoItem(
            project_id=project_id,
            name=name,
            description=description,
            url=url,
            deadline_utc=deadline_utc
        )
        self.session.add(todo)
        self.session.commit()
        return todo
    
    def delete_by_id(self, todo_id: int) -> bool:
        """Delete a todo item by id. Returns False if not found, raises DatabaseError on constraint violation."""
        todo = self.session.query(TodoItem).filter_by(id=todo_id).first()
        if not todo:
            return False
        self.session.delete(todo)
        self.session.commit()
        return True
    
    # == Update Methods ==
    
    def update_name(self, todo_id: int, new_name: str) -> bool:
        """Update todo item name. Returns False if not found."""
        todo = self.session.query(TodoItem).filter_by(id=todo_id).first()
        if not todo:
            return False
        todo.name = new_name
        self.session.commit()
        return True
    
    def update_description(self, todo_id: int, description: str) -> bool:
        """Update todo item description. Returns False if not found."""
        todo = self.session.query(TodoItem).filter_by(id=todo_id).first()
        if not todo:
            return False
        todo.description = description
        self.session.commit()
        return True
    
    def update_url(self, todo_id: int, url: str) -> bool:
        """Update todo item url. Returns False if not found."""
        todo = self.session.query(TodoItem).filter_by(id=todo_id).first()
        if not todo:
            return False
        todo.url = url
        self.session.commit()
        return True
    
    def update_deadline(self, todo_id: int, deadline_utc: datetime | None) -> bool:
        """Update todo item deadline. Returns False if not found."""
        todo = self.session.query(TodoItem).filter_by(id=todo_id).first()
        if not todo:
            return False
        todo.deadline_utc = deadline_utc  # type: ignore
        self.session.commit()
        return True
    
    def update_status(self, todo_id: int, status: str) -> bool:
        """Update todo item status. Returns False if not found."""
        todo = self.session.query(TodoItem).filter_by(id=todo_id).first()
        if not todo:
            return False
        todo.status = status
        # Handle completed_at_utc based on status
        if status == 'done':
            todo.completed_at_utc = datetime.now(timezone.utc)  # type: ignore
        else:
            todo.completed_at_utc = None
        self.session.commit()
        return True
    
    def toggle_status(self, todo_id: int) -> bool:
        """Toggle todo item status between active and done. Returns False if not found."""
        todo = self.session.query(TodoItem).filter_by(id=todo_id).first()
        if not todo:
            return False
        if todo.status == 'done':
            todo.status = 'active'
            todo.completed_at_utc = None
        else:
            todo.status = 'done'
            todo.completed_at_utc = datetime.now(timezone.utc)  # type: ignore
        self.session.commit()
        return True
    
    # == Move Operations ==
    
    def move_to_project(self, todo_id: int, project_id: int | None) -> bool:
        """Move a todo item to another project (or to box if project_id is None). Returns False if not found."""
        todo = self.session.query(TodoItem).filter_by(id=todo_id).first()
        if not todo:
            return False
        todo.project_id = project_id
        self.session.commit()
        return True
    
    # == Archive Operations ==
    
    def archive(self, todo_id: int) -> bool:
        """Archive a todo item. Returns False if not found."""
        todo = self.session.query(TodoItem).filter_by(id=todo_id).first()
        if not todo:
            return False
        todo.archived = True
        todo.archived_at_utc = datetime.now(timezone.utc)  # type: ignore
        self.session.commit()
        return True
    
    def unarchive(self, todo_id: int) -> bool:
        """Unarchive a todo item. Returns False if not found."""
        todo = self.session.query(TodoItem).filter_by(id=todo_id).first()
        if not todo:
            return False
        todo.archived = False
        todo.archived_at_utc = None
        self.session.commit()
        return True


# == IdeaItemService ========================================================

class IdeaItemService:
    def __init__(self):
        init_db()
        self.session = get_session()
    
    # == Basic CRUD ==
    
    def get_by_id(self, idea_id: int) -> IdeaItem | None:
        """Get an idea item by id. Returns None if not found."""
        return self.session.query(IdeaItem).filter_by(id=idea_id).first()
    
    def list_all(self, include_archived: bool = False) -> list[IdeaItem]:
        """List all idea items. By default filters out archived items."""
        query = self.session.query(IdeaItem)
        if not include_archived:
            query = query.filter_by(archived=False)
        return query.all()
    
    def add(
        self,
        name: str,
        description: str | None = None,
        maturity_hint: int | None = None,
        willingness_hint: int | None = None
    ) -> IdeaItem:
        """Create a new idea item. Raises DatabaseError on failure."""
        idea = IdeaItem(
            name=name,
            description=description,
            maturity_hint=maturity_hint,
            willingness_hint=willingness_hint
        )
        self.session.add(idea)
        self.session.commit()
        return idea
    
    def delete_by_id(self, idea_id: int) -> bool:
        """Delete an idea item by id. Returns False if not found, raises DatabaseError on constraint violation."""
        idea = self.session.query(IdeaItem).filter_by(id=idea_id).first()
        if not idea:
            return False
        self.session.delete(idea)
        self.session.commit()
        return True
    
    # == 更新方法 ==
    
    def update_name(self, idea_id: int, new_name: str) -> bool:
        """Update idea item name. Returns False if not found."""
        idea = self.session.query(IdeaItem).filter_by(id=idea_id).first()
        if not idea:
            return False
        idea.name = new_name
        self.session.commit()
        return True
    
    def update_description(self, idea_id: int, description: str) -> bool:
        """Update idea item description. Returns False if not found."""
        idea = self.session.query(IdeaItem).filter_by(id=idea_id).first()
        if not idea:
            return False
        idea.description = description
        self.session.commit()
        return True
    
    def update_hints(
        self,
        idea_id: int,
        maturity_hint: int | None = None,
        willingness_hint: int | None = None
    ) -> bool:
        """Update idea item hints. Returns False if not found."""
        idea = self.session.query(IdeaItem).filter_by(id=idea_id).first()
        if not idea:
            return False
        if maturity_hint is not None:
            idea.maturity_hint = maturity_hint
        if willingness_hint is not None:
            idea.willingness_hint = willingness_hint
        self.session.commit()
        return True
    
    def update_status(self, idea_id: int, status: str) -> bool:
        """Update idea item status. Returns False if not found."""
        idea = self.session.query(IdeaItem).filter_by(id=idea_id).first()
        if not idea:
            return False
        idea.status = status
        self.session.commit()
        return True
    
    # == Special Operations ==
    
    def promote_to_project(self, idea_id: int, project_id: int) -> bool:
        """Mark idea as promoted to a project. Returns False if not found."""
        idea = self.session.query(IdeaItem).filter_by(id=idea_id).first()
        if not idea:
            return False
        idea.status = 'promoted'
        idea.promoted_at_utc = datetime.now(timezone.utc)  # type: ignore
        idea.promoted_to_project_id = project_id
        self.session.commit()
        return True
    
    # == Archive Operations ==
    
    def archive(self, idea_id: int) -> bool:
        """Archive an idea item. Returns False if not found."""
        idea = self.session.query(IdeaItem).filter_by(id=idea_id).first()
        if not idea:
            return False
        idea.archived = True
        idea.archived_at_utc = datetime.now(timezone.utc)  # type: ignore
        self.session.commit()
        return True
    
    def unarchive(self, idea_id: int) -> bool:
        """Unarchive an idea item. Returns False if not found."""
        idea = self.session.query(IdeaItem).filter_by(id=idea_id).first()
        if not idea:
            return False
        idea.archived = False
        idea.archived_at_utc = None
        self.session.commit()
        return True


# == NowSessionService ========================================================

class NowSessionService:
    def __init__(self):
        init_db()
        self.session = get_session()
    
    # == Basic CRUD ==
    
    def get_by_id(self, session_id: int) -> NowSession | None:
        """Get a now session by id. Returns None if not found."""
        return self.session.query(NowSession).filter_by(id=session_id).first()
    
    def add(
        self,
        project_id: int | None,
        todo_item_id: int | None,
        duration_minutes: int,
        started_at_utc: datetime,
        ended_at_utc: datetime | None = None
    ) -> NowSession:
        """Create a new now session. ended_at_utc=None means ongoing session. Raises DatabaseError on failure."""
        now_session = NowSession(
            project_id=project_id,
            todo_item_id=todo_item_id,
            duration_minutes=duration_minutes,
            started_at_utc=started_at_utc,
            ended_at_utc=ended_at_utc
        )
        self.session.add(now_session)
        self.session.commit()
        return now_session
    
    def delete_by_id(self, session_id: int) -> bool:
        """Delete a now session by id. Returns False if not found."""
        now_session = self.session.query(NowSession).filter_by(id=session_id).first()
        if not now_session:
            return False
        self.session.delete(now_session)
        self.session.commit()
        return True
    
    # == List Queries ==
    
    def list_by_track_id(self, track_id: int) -> list[NowSession]:
        """List all now sessions for a track (via projects)."""
        return self.session.query(NowSession).join(Project).filter(Project.track_id == track_id).all()
    
    def list_by_project_id(self, project_id: int) -> list[NowSession]:
        """List all now sessions for a project."""
        return self.session.query(NowSession).filter_by(project_id=project_id).all()
    
    def list_by_todo_id(self, todo_id: int) -> list[NowSession]:
        """List all now sessions for a todo item."""
        return self.session.query(NowSession).filter_by(todo_item_id=todo_id).all()
    
    # == Special Methods ==
    
    def get_unfinished_session(self) -> NowSession | None:
        """Get the unfinished session (ended_at_utc is None). Returns None if not found."""
        return self.session.query(NowSession).filter_by(ended_at_utc=None).first()
    
    def update_ended_at(self, session_id: int, ended_at_utc: datetime) -> bool:
        """Update session end time. Returns False if not found."""
        now_session = self.session.query(NowSession).filter_by(id=session_id).first()
        if not now_session:
            return False
        now_session.ended_at_utc = ended_at_utc  # type: ignore
        self.session.commit()
        return True


