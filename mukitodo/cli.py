import typer
from typing_extensions import Annotated

app = typer.Typer(invoke_without_command=True, add_completion=False)


@app.callback()
def main(
    ctx: typer.Context,
    no_view: Annotated[bool, typer.Option("--no-view", help="Don't open TUI")] = False
):
    if ctx.invoked_subcommand is None:
        if not no_view:
            from mukitodo.view import run
            run()


@app.command()
def view():
    from mukitodo.view import run
    run()


@app.command(name="help")
def help_cmd():
    print("MukiTodo - Terminal Todo App")
    print()
    print("Usage:")
    print("  todo          Open TUI")
    print("  todo view     Open TUI")
    print("  todo help     Show this help")
    print()
    print("TUI Commands (COMMAND MODE):")
    print("  select <name> / enter <name>  Enter track/project")
    print("  back                          Go back")
    print("  add <name>                    Add track/project/item")
    print("  delete <name>                 Delete")
    print("  done <n>                      Mark item done")
    print("  undo <n>                      Mark item active")
    print("  list                          List items")
    print("  quit / q                      Exit")


if __name__ == "__main__":
    app()
