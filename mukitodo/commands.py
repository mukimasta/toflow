from mukitodo.services import TrackService, ProjectService, TodoItemService
from mukitodo.actions import Result


def execute(
    command: str,
    level: str,
    current_track: str | None = None,
    current_project: str | None = None,
) -> Result:
    parts = command.strip().split(maxsplit=1)
    if not parts:
        return Result("", None)

    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd in ("q", "quit"):
        return Result("Goodbye", None)

    if cmd in ("h", "?", "help"):
        return _help(level)

    if cmd in ("select", "enter"):
        return _select(arg, level, current_track)

    if cmd == "back":
        return _back(level)

    if cmd == "delete":
        return _delete(arg, level, current_track, current_project)

    if cmd == "done":
        return _done(arg, level, current_project)

    if cmd == "undo":
        return _undo(arg, level, current_project)

    if cmd.isdigit():
        if level == "items":
            return _done(cmd, level, current_project)
        else:
            return _select(cmd, level, current_track)

    return Result(f"Unknown command: {cmd}", False)


def _help(level: str) -> Result:
    if level == "tracks":
        msg = "add <name> | delete <name> | select <name> | list | quit"
    elif level == "projects":
        msg = "add <name> | delete <name> | select <name> | back | list | quit"
    else:
        msg = "add <content> | delete <n> | done <n> | undo <n> | back | list | quit"
    return Result(msg, True)


def _select(name: str, level: str, current_track: str | None) -> Result:
    if not name:
        return Result("Usage: select <name|index>", False)

    if level == "tracks":
        track_svc = TrackService()
        if name.isdigit():
            tracks = track_svc.list_all()
            idx = int(name) - 1
            if 0 <= idx < len(tracks):
                return Result(f"Use arrow keys to select track {name}", False)
            return Result(f"Track index {name} out of range", False)
        
        track = track_svc.get_by_name(name)
        if track:
            return Result(f"Use arrow keys to select track '{name}'", False)
        return Result(f"Track '{name}' not found", False)
    
    elif level == "projects":
        proj_svc = ProjectService()
        if name.isdigit():
            projects = proj_svc.list_by_track(current_track) if current_track else []
            idx = int(name) - 1
            if 0 <= idx < len(projects):
                return Result(f"Use arrow keys to select project {name}", False)
            return Result(f"Project index {name} out of range", False)
        
        proj = proj_svc.get_by_name(name)
        if proj:
            return Result(f"Use arrow keys to select project '{name}'", False)
        return Result(f"Project '{name}' not found", False)
    
    return Result("Cannot select in items view", False)


def _back(level: str) -> Result:
    if level == "items":
        return Result("Use arrow left to go back", False)
    elif level == "projects":
        return Result("Use arrow left to go back", False)
    return Result("Already at top level", False)


def _delete(name: str, level: str, current_track: str | None, current_project: str | None) -> Result:
    if not name:
        return Result("Usage: delete <name|index>", False)

    if level == "tracks":
        track_svc = TrackService()
        if name.isdigit():
            tracks = track_svc.list_all()
            idx = int(name) - 1
            if 0 <= idx < len(tracks):
                track_name = tracks[idx].name
                if track_svc.delete(track_name):
                    return Result(f"Track '{track_name}' deleted", True)
            return Result(f"Track index {name} out of range", False)
        
        if track_svc.delete(name):
            return Result(f"Track '{name}' deleted", True)
        return Result(f"Track '{name}' not found", False)
    
    elif level == "projects":
        proj_svc = ProjectService()
        if name.isdigit():
            projects = proj_svc.list_by_track(current_track) if current_track else []
            idx = int(name) - 1
            if 0 <= idx < len(projects):
                proj_name = projects[idx].name
                if proj_svc.delete(proj_name):
                    return Result(f"Project '{proj_name}' deleted", True)
            return Result(f"Project index {name} out of range", False)
        
        if proj_svc.delete(name):
            return Result(f"Project '{name}' deleted", True)
        return Result(f"Project '{name}' not found", False)
    
    else:
        item_svc = TodoItemService()
        if item_svc.delete(current_project, name) if current_project else False:
            return Result("Item deleted", True)
        return Result("Item not found", False)


def _done(identifier: str, level: str, current_project: str | None) -> Result:
    if level != "items":
        return Result("done only works in items view", False)
    if not identifier:
        return Result("Usage: done <name|index>", False)

    item_svc = TodoItemService()
    if item_svc.mark_done(current_project, identifier) if current_project else False:
        return Result("Marked as done", True)
    return Result("Item not found", False)


def _undo(identifier: str, level: str, current_project: str | None) -> Result:
    if level != "items":
        return Result("undo only works in items view", False)
    if not identifier:
        return Result("Usage: undo <name|index>", False)

    item_svc = TodoItemService()
    if item_svc.mark_undo(current_project, identifier) if current_project else False:
        return Result("Marked as active", True)
    return Result("Item not found", False)
