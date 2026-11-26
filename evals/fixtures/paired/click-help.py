from pathlib import Path
import sys

sys.path.insert(0, str(Path("src").resolve()))
import click

option = click.Option(["--mode"], help="", deprecated=True)
with click.Context(click.Command("demo")) as context:
    assert option.get_help_record(context)[1] == "(DEPRECATED)"
