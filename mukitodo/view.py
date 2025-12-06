from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl, BufferControl, ConditionalContainer
from prompt_toolkit.styles import Style
from prompt_toolkit.filters import Condition

from mukitodo.commands import execute, Context, Result
from mukitodo.services import TrackService, ProjectService, TodoItemService


class ViewState:
    def __init__(self):
        self.mode = "normal"
        self.view = "main"
        self.current_track: str | None = None
        self.current_project: str | None = None
        self.cursor = 0
        self.last_message = ""
        self.last_success: bool | None = None
        self._items: list[tuple[str, str]] = []

    def get_context(self) -> Context:
        return Context(
            view=self.view,
            current_track=self.current_track,
            current_project=self.current_project,
        )

    def load_items(self):
        self._items = []
        if self.view == "main":
            track_svc = TrackService()
            proj_svc = ProjectService()
            tracks = track_svc.list_all()

            if not self.current_track:
                for t in tracks:
                    self._items.append(("track", t.name))
                    for p in proj_svc.list_by_track(t.name):
                        self._items.append(("project", p.name))
            else:
                for p in proj_svc.list_by_track(self.current_track):
                    self._items.append(("project", p.name))
        else:
            item_svc = TodoItemService()
            for item in item_svc.list_by_project(self.current_project):
                status = "done" if item.status == "completed" else "active"
                self._items.append((status, item.content))

        if self.cursor >= len(self._items):
            self.cursor = max(0, len(self._items) - 1)

    def get_current_item(self) -> tuple[str, str] | None:
        if 0 <= self.cursor < len(self._items):
            return self._items[self.cursor]
        return None

    def handle_result(self, result: Result):
        self.last_message = result.message
        self.last_success = result.success

        if result.action == "quit":
            return "quit"

        if result.action == "select_track":
            self.current_track = result.target
            self.cursor = 0
        elif result.action == "select_project":
            self.current_project = result.target
            self.view = "project"
            self.cursor = 0
        elif result.action == "back_to_main":
            self.view = "main"
            self.cursor = 0
        elif result.action == "back_to_tracks":
            self.current_track = None
            self.cursor = 0

        self.load_items()
        return None

    def move_cursor(self, delta: int):
        if self._items:
            self.cursor = max(0, min(len(self._items) - 1, self.cursor + delta))

    def select_current(self) -> Result | None:
        item = self.get_current_item()
        if not item:
            return None

        item_type, name = item
        if item_type == "track":
            return execute(f"select {name}", self.get_context())
        elif item_type == "project":
            return execute(f"select {name}", self.get_context())
        return None

    def toggle_current_item(self) -> Result | None:
        if self.view != "project":
            return None
        item = self.get_current_item()
        if not item:
            return None
        status, _ = item
        idx = str(self.cursor + 1)
        if status == "done":
            return execute(f"undo {idx}", self.get_context())
        else:
            return execute(f"done {idx}", self.get_context())

    def go_back(self) -> Result:
        return execute("back", self.get_context())


def run():
    state = ViewState()
    state.load_items()

    input_buffer = Buffer()

    def get_main_content():
        state.load_items()
        lines = []

        if state.view == "main":
            if state.current_track:
                lines.append(("class:header", f"  Track: {state.current_track}\n\n"))
                if not state._items:
                    lines.append(("class:dim", "  No projects. Press : then 'add <name>'\n"))
            elif not state._items:
                lines.append(("class:dim", "No tracks. Press : then 'add <name>'\n"))

            for idx, (item_type, name) in enumerate(state._items):
                is_selected = idx == state.cursor
                if item_type == "track":
                    prefix = "▸ " if is_selected else "  "
                    style = "class:selected" if is_selected else "class:track"
                    lines.append((style, f"{prefix}{name}\n"))
                else:
                    prefix = "  ▸ " if is_selected else "    "
                    style = "class:selected" if is_selected else ""
                    lines.append((style, f"{prefix}{name}\n"))
        else:
            lines.append(("class:header", f"  Project: {state.current_project}\n\n"))
            if not state._items:
                lines.append(("class:dim", "  No items. Press : to add items.\n"))
            else:
                for idx, (status, content) in enumerate(state._items):
                    is_selected = idx == state.cursor
                    marker = "✓" if status == "done" else "○"
                    prefix = "▸ " if is_selected else "  "
                    num = f"{idx + 1}."
                    style = "class:selected" if is_selected else ("class:done" if status == "done" else "")
                    lines.append((style, f"{prefix}{num:3} {marker} {content}\n"))

        return lines

    def get_status_line():
        if state.last_message:
            style = "class:success" if state.last_success else "class:error"
            return [(style, f"  {state.last_message}")]
        if state.mode == "command":
            return [("class:dim", "  [Enter] execute  [q/Ctrl+G] exit command mode")]
        if state.view == "project":
            return [("class:dim", "  [↑↓] move  [Space] toggle done  [←] back  [:] command")]
        return [("class:dim", "  [↑↓] move  [→/Enter] select  [←] back  [:] command")]

    def get_mode_indicator():
        if state.mode == "command":
            return [("class:mode", " COMMAND ")]
        return [("class:mode", " NORMAL ")]

    def get_prompt():
        return [("class:prompt", "> ")]

    kb = KeyBindings()

    is_normal = Condition(lambda: state.mode == "normal")
    is_command = Condition(lambda: state.mode == "command")

    @kb.add("c-c")
    @kb.add("c-d")
    def _(event):
        event.app.exit()

    @kb.add("up", filter=is_normal)
    @kb.add("w", filter=is_normal)
    def _(event):
        state.move_cursor(-1)

    @kb.add("down", filter=is_normal)
    @kb.add("s", filter=is_normal)
    def _(event):
        state.move_cursor(1)

    @kb.add("right", filter=is_normal)
    @kb.add("d", filter=is_normal)
    @kb.add("]", filter=is_normal)
    @kb.add("enter", filter=is_normal)
    def _(event):
        result = state.select_current()
        if result:
            state.handle_result(result)

    @kb.add("space", filter=is_normal)
    def _(event):
        if state.view == "project":
            result = state.toggle_current_item()
            if result:
                state.handle_result(result)
        else:
            result = state.select_current()
            if result:
                state.handle_result(result)

    @kb.add("left", filter=is_normal)
    @kb.add("a", filter=is_normal)
    @kb.add("[", filter=is_normal)
    def _(event):
        result = state.go_back()
        state.handle_result(result)

    @kb.add(":", filter=is_normal)
    @kb.add(">", filter=is_normal)
    def _(event):
        state.mode = "command"
        state.last_message = ""
        state.last_success = None

    @kb.add("escape", filter=is_command)
    @kb.add("c-g", filter=is_command)
    def _(event):
        state.mode = "normal"
        input_buffer.reset()

    @kb.add("q", filter=is_command)
    def _(event):
        if not input_buffer.text:
            state.mode = "normal"
        else:
            input_buffer.insert_text("q")

    @kb.add("enter", filter=is_command)
    def _(event):
        cmd = input_buffer.text.strip()
        input_buffer.reset()

        if not cmd:
            return

        if cmd.lower() in ("q", "quit"):
            event.app.exit()
            return

        result = execute(cmd, state.get_context())
        action = state.handle_result(result)
        if action == "quit":
            event.app.exit()

    layout = Layout(
        HSplit([
            Window(content=FormattedTextControl(get_main_content), wrap_lines=True),
            Window(height=1, char="─", style="class:separator"),
            Window(content=FormattedTextControl(get_status_line), height=1),
            ConditionalContainer(
                HSplit([
                    VSplit([
                        Window(content=FormattedTextControl(get_mode_indicator), width=10),
                        Window(content=FormattedTextControl(get_prompt), width=2),
                        Window(content=BufferControl(buffer=input_buffer)),
                    ], height=1),
                ]),
                filter=is_command,
            ),
        ])
    )

    style = Style.from_dict({
        "dim": "ansibrightblack",
        "track": "bold",
        "selected": "reverse",
        "header": "bold ansiblue",
        "done": "ansibrightblack",
        "success": "ansigreen",
        "error": "ansired",
        "separator": "ansibrightblack",
        "mode": "bg:ansiblue ansiwhite",
        "prompt": "bold",
    })

    app = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=True,
    )

    app.run()
