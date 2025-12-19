from dataclasses import dataclass
from enum import Enum

from mukitodo.services import TrackService, ProjectService, TodoItemService
from mukitodo.models import Track, Project, TodoItem


@dataclass
class Result:
    message: str = ""
    success: bool | None = None

EmptyResult = Result("", None)


def list_tracks() -> list[Track]:
    return TrackService().list_all()


def list_projects(track_id: int) -> list[Project]:
    return ProjectService().list_by_track_id(track_id)


def list_todos(project_id: int) -> list[TodoItem]:
    return TodoItemService().list_by_project_id(project_id)


def get_track(track_id: int) -> Track | None:
    return TrackService().get_by_id(track_id)


def get_project(project_id: int) -> Project | None:
    return ProjectService().get_by_id(project_id)


def get_todo(todo_id: int) -> TodoItem | None:
    return TodoItemService().get_by_id(todo_id)


def add_track(name: str) -> Result:
    if not name:
        return Result("Track name required", False)
    track = TrackService().add(name)
    if track:
        return Result(f"Track '{name}' created", True)
    return Result("Failed to create track", False)


def add_project(track_id: int, name: str) -> Result:
    if not name:
        return Result("Project name required", False)
    project = ProjectService().add_by_track_id(track_id, name)
    if project:
        return Result(f"Project '{name}' created", True)
    return Result("Failed to create project", False)


def add_todo(project_id: int, content: str) -> Result:
    if not content:
        return Result("Todo content required", False)
    item = TodoItemService().add_by_project_id(project_id, content)
    if item:
        return Result("Todo added", True)
    return Result("Failed to add todo", False)


def delete_track(track_id: int) -> Result:
    track = TrackService().get_by_id(track_id)
    if not track:
        return Result("Track not found", False)
    track_name = track.name
    if TrackService().delete_by_id(track_id):
        return Result(f"Track '{track_name}' deleted", True)
    return Result("Failed to delete track", False)


def delete_project(project_id: int) -> Result:
    project = ProjectService().get_by_id(project_id)
    if not project:
        return Result("Project not found", False)
    project_name = project.name
    if ProjectService().delete_by_id(project_id):
        return Result(f"Project '{project_name}' deleted", True)
    return Result("Failed to delete project", False)


def delete_todo(todo_id: int) -> Result:
    if TodoItemService().delete_by_id(todo_id):
        return Result("Todo deleted", True)
    return Result("Todo not found", False)


def toggle_todo(todo_id: int) -> Result:
    item = TodoItemService().get_by_id(todo_id)
    if not item:
        return Result("Todo not found", False)
    
    if TodoItemService().toggle_by_id(todo_id):
        status = "completed" if item.status == "active" else "active"
        return Result(f"Todo marked as {status}", True)
    return Result("Failed to toggle todo", False)


def rename_track(track_id: int, new_name: str) -> Result:
    if not new_name:
        return Result("Track name required", False)
    track = TrackService().get_by_id(track_id)
    if not track:
        return Result("Track not found", False)
    old_name = track.name
    if TrackService().rename(track_id, new_name):
        return Result(f"Track renamed from '{old_name}' to '{new_name}'", True)
    return Result("Failed to rename track", False)


def rename_project(project_id: int, new_name: str) -> Result:
    if not new_name:
        return Result("Project name required", False)
    project = ProjectService().get_by_id(project_id)
    if not project:
        return Result("Project not found", False)
    old_name = project.name
    if ProjectService().rename(project_id, new_name):
        return Result(f"Project renamed from '{old_name}' to '{new_name}'", True)
    return Result("Failed to rename project", False)


def rename_todo(todo_id: int, new_content: str) -> Result:
    if not new_content:
        return Result("Todo content required", False)
    todo = TodoItemService().get_by_id(todo_id)
    if not todo:
        return Result("Todo not found", False)
    if TodoItemService().rename(todo_id, new_content):
        return Result(f"Todo renamed to '{new_content}'", True)
    return Result("Failed to rename todo", False)
