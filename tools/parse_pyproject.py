# -*- coding:  utf-8 -*-
"""Parse pyproject.toml and return its values.

Useful for shell scripts to know more about OpenPype build.
"""
import os
import blessed
import toml
from pathlib import Path
import click

term = blessed.Terminal()


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

    print("{}{}".format(header, msg))


@click.command()
@click.argument("key", nargs=-1, type=click.STRING)
def main(key):
    _print("Reading build metadata ...")
    openpype_root = Path(os.path.dirname(__file__)).parent
    py_project = toml.load(openpype_root / "pyproject.toml")
    query = key.split(".")
    data = py_project
    for k in query:
        if isinstance(data, dict):
            data = data.get(k)
        else:
            break
    print(data)


if __name__ == "__main__":
    main()
