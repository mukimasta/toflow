from dataclasses import dataclass
from mukitodo.services import TrackService, ProjectService, TodoItemService


@dataclass
class Context:
    view: str = "main"
    current_track: str | None = None
    current_project: str | None = None


@dataclass
class Result:
    success: bool | None
    message: str
    action: str | None = None
    target: str | None = None


def execute(command: str, ctx: Context) -> Result:
    parts = command.strip().split(maxsplit=1)
    if not parts:
        return Result(None, "")

    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd in ("q", "quit"):
        return Result(None, "", action="quit")

    if cmd in ("h", "?", "help"):
        return _help(ctx)

    if cmd in ("select", "enter"):
        return _select(arg, ctx)

    if cmd == "back":
        return _back(ctx)

    if cmd == "add":
        return _add(arg, ctx)

    if cmd == "list":
        return _list(ctx)

    if cmd == "delete":
        return _delete(arg, ctx)

    if cmd == "done":
        return _done(arg, ctx)

    if cmd == "undo":
        return _undo(arg, ctx)

    return Result(False, f"Unknown command: {cmd}")


def _help(ctx: Context) -> Result:
    if ctx.view == "main":
        if ctx.current_track:
            msg = "add <name> | delete <name> | select <name> | back | list | quit"
        else:
            msg = "add <name> | delete <name> | select <name> | list | quit"
    else:
        msg = "add <content> | delete <n> | done <n> | undo <n> | back | list | quit"
    return Result(True, msg)


def _select(name: str, ctx: Context) -> Result:
    if not name:
        return Result(False, "Usage: select <name>")

    if ctx.view == "main":
        if not ctx.current_track:
            track_svc = TrackService()
            track = track_svc.get_by_name(name)
            if track:
                return Result(True, f"Entered track: {name}", action="select_track", target=name)
            proj_svc = ProjectService()
            proj = proj_svc.get_by_name(name)
            if proj:
                return Result(True, f"Entered project: {name}", action="select_project", target=name)
            return Result(False, f"'{name}' not found")
        else:
            proj_svc = ProjectService()
            proj = proj_svc.get_by_name(name)
            if proj and proj.track.name == ctx.current_track:
                return Result(True, f"Entered project: {name}", action="select_project", target=name)
            return Result(False, f"Project '{name}' not found in {ctx.current_track}")
    else:
        return Result(False, "Already in project view")


def _back(ctx: Context) -> Result:
    if ctx.view == "project":
        return Result(True, "Back to main view", action="back_to_main")
    elif ctx.current_track:
        return Result(True, "Back to tracks", action="back_to_tracks")
    else:
        return Result(False, "Already at top level")


def _add(name: str, ctx: Context) -> Result:
    if not name:
        return Result(False, "Usage: add <name>")

    if ctx.view == "main":
        if not ctx.current_track:
            track_svc = TrackService()
            track = track_svc.add(name)
            return Result(True, f"Track '{track.name}' created")
        else:
            proj_svc = ProjectService()
            proj = proj_svc.add(ctx.current_track, name)
            if proj:
                return Result(True, f"Project '{proj.name}' created")
            return Result(False, f"Failed to create project")
    else:
        item_svc = TodoItemService()
        item = item_svc.add(ctx.current_project, name)
        if item:
            return Result(True, f"Item added")
        return Result(False, "Failed to add item")


def _list(ctx: Context) -> Result:
    if ctx.view == "main":
        if not ctx.current_track:
            track_svc = TrackService()
            tracks = track_svc.list_all()
            if tracks:
                return Result(True, ", ".join(t.name for t in tracks))
            return Result(True, "No tracks")
        else:
            proj_svc = ProjectService()
            projects = proj_svc.list_by_track(ctx.current_track)
            if projects:
                return Result(True, ", ".join(p.name for p in projects))
            return Result(True, "No projects")
    else:
        item_svc = TodoItemService()
        items = item_svc.list_by_project(ctx.current_project)
        if items:
            lines = [f"{'✓' if i.status == 'completed' else '○'} {i.content}" for i in items]
            return Result(True, "\n".join(lines))
        return Result(True, "No items")


def _delete(name: str, ctx: Context) -> Result:
    if not name:
        return Result(False, "Usage: delete <name>")

    if ctx.view == "main":
        if not ctx.current_track:
            track_svc = TrackService()
            if track_svc.delete(name):
                return Result(True, f"Track '{name}' deleted")
            return Result(False, f"Track '{name}' not found")
        else:
            proj_svc = ProjectService()
            if proj_svc.delete(name):
                return Result(True, f"Project '{name}' deleted")
            return Result(False, f"Project '{name}' not found")
    else:
        item_svc = TodoItemService()
        if item_svc.delete(ctx.current_project, name):
            return Result(True, "Item deleted")
        return Result(False, "Item not found")


def _done(identifier: str, ctx: Context) -> Result:
    if ctx.view != "project":
        return Result(False, "done only works in project view")
    if not identifier:
        return Result(False, "Usage: done <name|index>")

    item_svc = TodoItemService()
    if item_svc.mark_done(ctx.current_project, identifier):
        return Result(True, "Marked as done")
    return Result(False, "Item not found")


def _undo(identifier: str, ctx: Context) -> Result:
    if ctx.view != "project":
        return Result(False, "undo only works in project view")
    if not identifier:
        return Result(False, "Usage: undo <name|index>")

    item_svc = TodoItemService()
    if item_svc.mark_undo(ctx.current_project, identifier):
        return Result(True, "Marked as active")
    return Result(False, "Item not found")
