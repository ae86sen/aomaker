import functools
from rich.console import Console
console = Console()

def printer(start_msg, end_msg):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            console.print(f"[bold blue]<AoMaker> :hourglass_flowing_sand: {start_msg}[/bold blue]")

            result = func(*args, **kwargs)

            console.print(f"[bold green]<AoMaker> :white_check_mark: {end_msg}[/bold green]")

            return result
        return wrapper
    return decorator

def print_message(message, style="bold blue"):
    console.print(f"[{style}]<AoMaker> {message}[/{style}]")
