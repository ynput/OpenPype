"""OpenColorIO Wrapper.

Only to be interpreted by Python 3. It is runned in subprocess in case
Python 2 hosts needs to use it. Or it is used as modul for Python 3
processing.

Providing functionality:
- get_colorspace - console command - python 2
                 - returning all available colorspaces
                   found in input config path.
- get_colorspace_data - python 3 - module function
                      - returning all available colorspaces
                        found in input config path.
- get_views - console command - python 2
            - returning all available viewers
              found in input config path.
- get_views_data - python 3 - module function
                 - returning all available viewers
                   found in input config path.
"""

import click
import json
from pathlib2 import Path
import PyOpenColorIO as ocio


@click.group()
def main():
    pass


@main.group()
def config():
    """Config related commands group

    Example of use:
    > pyton.exe ./ocio_wrapper.py config <command> *args
    """
    pass


@config.command(
    name="get_colorspace",
    help=(
        "return all colorspaces from config file "
        "--path input arg is required"
    )
)
@click.option("--in_path", required=True,
              help="path where to read ocio config file",
              type=click.Path(exists=True))
@click.option("--out_path", required=True,
              help="path where to write output json file",
              type=click.Path())
def get_colorspace(in_path, out_path):
    """Agregate all colorspace to file.

    Python 2 wrapped console command

    Args:
        in_path (str): config file path string
        out_path (str): temp json file path string

    Example of use:
    > pyton.exe ./ocio_wrapper.py config get_colorspace
        --in_path=<path> --out_path=<path>
    """
    json_path = Path(out_path)

    out_data = get_colorspace_data(in_path)

    with open(json_path, "w") as f:
        json.dump(out_data, f)

    print(f"Colorspace data are saved to '{json_path}'")


def get_colorspace_data(config_path):
    """Return all found colorspace data.

    Args:
        config_path (str): path string leading to config.ocio

    Raises:
        IOError: Input config does not exists.

    Returns:
        dict: aggregated available colorspaces
    """
    config_path = Path(config_path)

    if not config_path.is_file():
        raise IOError(
            f"Input path `{config_path}` should be `config.ocio` file")

    config = ocio.Config().CreateFromFile(str(config_path))

    return {
        c.getName(): c.getFamily()
        for c in config.getColorSpaces()
    }


@config.command(
    name="get_views",
    help=(
        "return all viewers from config file "
        "--path input arg is required"
    )
)
@click.option("--in_path", required=True,
              help="path where to read ocio config file",
              type=click.Path(exists=True))
@click.option("--out_path", required=True,
              help="path where to write output json file",
              type=click.Path())
def get_views(in_path, out_path):
    """Agregate all viewers to file.

    Python 2 wrapped console command

    Args:
        in_path (str): config file path string
        out_path (str): temp json file path string

    Example of use:
    > pyton.exe ./ocio_wrapper.py config get_views \
        --in_path=<path> --out_path=<path>
    """
    json_path = Path(out_path)

    out_data = get_views_data(in_path)

    with open(json_path, "w") as f:
        json.dump(out_data, f)

    print(f"Viewer data are saved to '{json_path}'")


def get_views_data(config_path):
    """Return all found viewer data.

    Args:
        config_path (str): path string leading to config.ocio

    Raises:
        IOError: Input config does not exists.

    Returns:
        dict: aggregated available viewers
    """
    config_path = Path(config_path)

    if not config_path.is_file():
        raise IOError("Input path should be `config.ocio` file")

    config = ocio.Config().CreateFromFile(str(config_path))

    return {
        f"{d}/{v}": {"display": d, "view": v}
        for d in config.getDisplays()
        for v in config.getViews(d)
    }


if __name__ == '__main__':
    main()
