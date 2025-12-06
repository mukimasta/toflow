from datetime import datetime
from mukitodo.database import get_session, init_db
from mukitodo.models import Track, Project, TodoItem


class TrackService:
    def __init__(self):
        init_db()
        self.session = get_session()

    def add(self, name: str) -> Track:
        track = Track(name=name)
        self.session.add(track)
        self.session.commit()
        return track

    def get_by_name(self, name: str) -> Track | None:
        return self.session.query(Track).filter_by(name=name).first()

    def list_all(self) -> list[Track]:
        return self.session.query(Track).all()

    def delete(self, name: str) -> bool:
        track = self.session.query(Track).filter_by(name=name).first()
        if track:
            self.session.delete(track)
            self.session.commit()
            return True
        return False


class ProjectService:
    def __init__(self):
        init_db()
        self.session = get_session()

    def add(self, track_name: str, project_name: str) -> Project | None:
        track = self.session.query(Track).filter_by(name=track_name).first()
        if not track:
            return None
        project = Project(name=project_name, track_id=track.id)
        self.session.add(project)
        self.session.commit()
        return project

    def list_by_track(self, track_name: str) -> list[Project]:
        track = self.session.query(Track).filter_by(name=track_name).first()
        if not track:
            return []
        return self.session.query(Project).filter_by(track_id=track.id).all()

    def list_all(self) -> list[Project]:
        return self.session.query(Project).all()

    def delete(self, name: str) -> bool:
        project = self.session.query(Project).filter_by(name=name).first()
        if project:
            self.session.delete(project)
            self.session.commit()
            return True
        return False

    def get_by_name(self, name: str) -> Project | None:
        return self.session.query(Project).filter_by(name=name).first()


class TodoItemService:
    def __init__(self):
        init_db()
        self.session = get_session()

    def add(self, project_name: str, content: str) -> TodoItem | None:
        project = self.session.query(Project).filter_by(name=project_name).first()
        if not project:
            return None
        item = TodoItem(content=content, project_id=project.id)
        self.session.add(item)
        self.session.commit()
        return item

    def list_by_project(self, project_name: str) -> list[TodoItem]:
        project = self.session.query(Project).filter_by(name=project_name).first()
        if not project:
            return []
        return self.session.query(TodoItem).filter_by(project_id=project.id).all()

    def get_by_content_or_index(self, project_name: str, identifier: str) -> TodoItem | None:
        items = self.list_by_project(project_name)
        if not items:
            return None
        if identifier.isdigit():
            idx = int(identifier) - 1
            if 0 <= idx < len(items):
                return items[idx]
            return None
        for item in items:
            if item.content == identifier:
                return item
        return None

    def mark_done(self, project_name: str, identifier: str) -> bool:
        item = self.get_by_content_or_index(project_name, identifier)
        if item:
            item.status = "completed"
            item.completed_at = datetime.now()
            self.session.commit()
            return True
        return False

    def mark_undo(self, project_name: str, identifier: str) -> bool:
        item = self.get_by_content_or_index(project_name, identifier)
        if item:
            item.status = "active"
            item.completed_at = None
            self.session.commit()
            return True
        return False

    def delete(self, project_name: str, identifier: str) -> bool:
        item = self.get_by_content_or_index(project_name, identifier)
        if item:
            self.session.delete(item)
            self.session.commit()
            return True
        return False

