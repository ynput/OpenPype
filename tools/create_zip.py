# -*- coding: utf-8 -*-
"""Create OpenPype version from live sources."""
from igniter import bootstrap_repos
import click
import enlighten
import blessed
from pathlib2 import Path


term = blessed.Terminal()
manager = enlighten.get_manager()
last_increment = 0


@click.group(invoke_without_command=True)
@click.option("--path", required=False,
              help="path where to put version",
              type=click.Path(exists=True))
def main(path):
    # create zip file

    progress_bar = enlighten.Counter(
        total=100, desc="OpenPype ZIP", units="%", color="green")

    def progress(inc: int):
        """Progress handler."""
        global last_increment
        progress_bar.update(incr=inc - last_increment)
        last_increment = inc

    bs = bootstrap_repos.BootstrapRepos(progress_callback=progress)
    if path:
        out_path = Path(path)
        bs.data_dir = out_path
        if out_path.is_file():
            bs.data_dir = out_path.parent

    _print(f"Creating zip in {bs.data_dir} ...")
    repo_file = bs.create_version_from_live_code()
    if not repo_file:
        _print("Error while creating zip file.", 1)
        exit(1)

    _print(f"Created {repo_file}")


def _print(msg: str, message_type: int = 0) -> None:
    """Print message to console.

    Args:
        msg (str): message to print
        message_type (int): type of message (0 info, 1 error, 2 note)

    """
    if message_type == 0:
        header = term.aquamarine3(">>> ")
    elif message_type == 1:
        header = term.orangered2("!!! ")
    elif message_type == 2:
        header = term.tan1("... ")
    else:
        header = term.darkolivegreen3("--- ")

    print(f"{header}{msg}")


if __name__ == "__main__":
    main()
