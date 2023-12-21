"""OpenColorIO Wrapper.

Only to be interpreted by Python 3. It is run in subprocess in case
Python 2 hosts needs to use it. Or it is used as module for Python 3
processing.

Providing functionality:
- get_colorspace - console command - python 2
                 - returning all available color spaces
                   found in input config path.
- _get_colorspace_data - python 3 - module function
                      - returning all available colorspaces
                        found in input config path.
- get_views - console command - python 2
            - returning all available viewers
              found in input config path.
- _get_views_data - python 3 - module function
                 - returning all available viewers
                   found in input config path.
"""

import click
import json
from pathlib import Path
import PyOpenColorIO as ocio


@click.group()
def main():
    pass  # noqa: WPS100


@main.group()
def config():
    """Config related commands group

    Example of use:
    > pyton.exe ./ocio_wrapper.py config <command> *args
    """
    pass  # noqa: WPS100


@main.group()
def colorspace():
    """Colorspace related commands group

    Example of use:
    > pyton.exe ./ocio_wrapper.py config <command> *args
    """
    pass  # noqa: WPS100


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
    """Aggregate all colorspace to file.

    Python 2 wrapped console command

    Args:
        in_path (str): config file path string
        out_path (str): temp json file path string

    Example of use:
    > pyton.exe ./ocio_wrapper.py config get_colorspace
        --in_path=<path> --out_path=<path>
    """
    json_path = Path(out_path)

    out_data = _get_colorspace_data(in_path)

    with open(json_path, "w") as f_:
        json.dump(out_data, f_)

    print(f"Colorspace data are saved to '{json_path}'")


def _get_colorspace_data(config_path):
    """Return all found colorspace data.

    Args:
        config_path (str): path string leading to config.ocio

    Raises:
        IOError: Input config does not exist.

    Returns:
        dict: aggregated available colorspaces
    """
    config_path = Path(config_path)

    if not config_path.is_file():
        raise IOError(
            f"Input path `{config_path}` should be `config.ocio` file")

    config = ocio.Config().CreateFromFile(str(config_path))

    colorspace_data = {
        "roles": {},
        "colorspaces": {
            color.getName(): {
                "family": color.getFamily(),
                "categories": list(color.getCategories()),
                "aliases": list(color.getAliases()),
                "equalitygroup": color.getEqualityGroup(),
            }
            for color in config.getColorSpaces()
        },
        "displays_views": {
            f"{view} ({display})": {
                "display": display,
                "view": view

            }
            for display in config.getDisplays()
            for view in config.getViews(display)
        },
        "looks": {}
    }

    # add looks
    looks = config.getLooks()
    if looks:
        colorspace_data["looks"] = {
            look.getName(): {"process_space": look.getProcessSpace()}
            for look in looks
        }

    # add roles
    roles = config.getRoles()
    if roles:
        colorspace_data["roles"] = {
            role: {"colorspace": colorspace}
            for (role, colorspace) in roles
        }

    return colorspace_data


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
    """Aggregate all viewers to file.

    Python 2 wrapped console command

    Args:
        in_path (str): config file path string
        out_path (str): temp json file path string

    Example of use:
    > pyton.exe ./ocio_wrapper.py config get_views \
        --in_path=<path> --out_path=<path>
    """
    json_path = Path(out_path)

    out_data = _get_views_data(in_path)

    with open(json_path, "w") as f_:
        json.dump(out_data, f_)

    print(f"Viewer data are saved to '{json_path}'")


def _get_views_data(config_path):
    """Return all found viewer data.

    Args:
        config_path (str): path string leading to config.ocio

    Raises:
        IOError: Input config does not exist.

    Returns:
        dict: aggregated available viewers
    """
    config_path = Path(config_path)

    if not config_path.is_file():
        raise IOError("Input path should be `config.ocio` file")

    config = ocio.Config().CreateFromFile(str(config_path))

    data_ = {}
    for display in config.getDisplays():
        for view in config.getViews(display):
            colorspace = config.getDisplayViewColorSpaceName(display, view)
            # Special token. See https://opencolorio.readthedocs.io/en/latest/guides/authoring/authoring.html#shared-views # noqa
            if colorspace == "<USE_DISPLAY_NAME>":
                colorspace = display

            data_[f"{display}/{view}"] = {
                "display": display,
                "view": view,
                "colorspace": colorspace
            }

    return data_


@config.command(
    name="get_version",
    help=(
        "return major and minor version from config file "
        "--config_path input arg is required"
        "--out_path input arg is required"
    )
)
@click.option("--config_path", required=True,
              help="path where to read ocio config file",
              type=click.Path(exists=True))
@click.option("--out_path", required=True,
              help="path where to write output json file",
              type=click.Path())
def get_version(config_path, out_path):
    """Get version of config.

    Python 2 wrapped console command

    Args:
        config_path (str): ocio config file path string
        out_path (str): temp json file path string

    Example of use:
    > pyton.exe ./ocio_wrapper.py config get_version \
        --config_path=<path> --out_path=<path>
    """
    json_path = Path(out_path)

    out_data = _get_version_data(config_path)

    with open(json_path, "w") as f_:
        json.dump(out_data, f_)

    print(f"Config version data are saved to '{json_path}'")


def _get_version_data(config_path):
    """Return major and minor version info.

    Args:
        config_path (str): path string leading to config.ocio

    Raises:
        IOError: Input config does not exist.

    Returns:
        dict: minor and major keys with values
    """
    config_path = Path(config_path)

    if not config_path.is_file():
        raise IOError("Input path should be `config.ocio` file")

    config = ocio.Config().CreateFromFile(str(config_path))

    return {
        "major": config.getMajorVersion(),
        "minor": config.getMinorVersion()
    }


@colorspace.command(
    name="get_config_file_rules_colorspace_from_filepath",
    help=(
        "return colorspace from filepath "
        "--config_path - ocio config file path (input arg is required) "
        "--filepath - any file path (input arg is required) "
        "--out_path - temp json file path (input arg is required)"
    )
)
@click.option("--config_path", required=True,
              help="path where to read ocio config file",
              type=click.Path(exists=True))
@click.option("--filepath", required=True,
              help="path to file to get colorspace from",
              type=click.Path())
@click.option("--out_path", required=True,
              help="path where to write output json file",
              type=click.Path())
def get_config_file_rules_colorspace_from_filepath(
    config_path, filepath, out_path
):
    """Get colorspace from file path wrapper.

    Python 2 wrapped console command

    Args:
        config_path (str): config file path string
        filepath (str): path string leading to file
        out_path (str): temp json file path string

    Example of use:
    > pyton.exe ./ocio_wrapper.py \
        colorspace get_config_file_rules_colorspace_from_filepath \
        --config_path=<path> --filepath=<path> --out_path=<path>
    """
    json_path = Path(out_path)

    colorspace = _get_config_file_rules_colorspace_from_filepath(
        config_path, filepath)

    with open(json_path, "w") as f_:
        json.dump(colorspace, f_)

    print(f"Colorspace name is saved to '{json_path}'")


def _get_config_file_rules_colorspace_from_filepath(config_path, filepath):
    """Return found colorspace data found in v2 file rules.

    Args:
        config_path (str): path string leading to config.ocio
        filepath (str): path string leading to v2 file rules

    Raises:
        IOError: Input config does not exist.

    Returns:
        dict: aggregated available colorspaces
    """
    config_path = Path(config_path)

    if not config_path.is_file():
        raise IOError(
            f"Input path `{config_path}` should be `config.ocio` file")

    config = ocio.Config().CreateFromFile(str(config_path))

    # TODO: use `parseColorSpaceFromString` instead if ocio v1
    colorspace = config.getColorSpaceFromFilepath(str(filepath))

    return colorspace


def _get_display_view_colorspace_name(config_path, display, view):
    """Returns the colorspace attribute of the (display, view) pair.

    Args:
        config_path (str): path string leading to config.ocio
        display (str): display name e.g. "ACES"
        view (str): view name e.g. "sRGB"


    Raises:
        IOError: Input config does not exist.

    Returns:
        view color space name (str) e.g. "Output - sRGB"
    """

    config_path = Path(config_path)

    if not config_path.is_file():
        raise IOError("Input path should be `config.ocio` file")

    config = ocio.Config.CreateFromFile(str(config_path))
    colorspace = config.getDisplayViewColorSpaceName(display, view)

    return colorspace


@config.command(
    name="get_display_view_colorspace_name",
    help=(
        "return default view colorspace name "
        "for the given display and view "
        "--path input arg is required"
    )
)
@click.option("--in_path", required=True,
              help="path where to read ocio config file",
              type=click.Path(exists=True))
@click.option("--out_path", required=True,
              help="path where to write output json file",
              type=click.Path())
@click.option("--display", required=True,
              help="display name",
              type=click.STRING)
@click.option("--view", required=True,
              help="view name",
              type=click.STRING)
def get_display_view_colorspace_name(in_path, out_path,
                                     display, view):
    """Aggregate view colorspace name to file.

    Wrapper command for processes without access to OpenColorIO

    Args:
        in_path (str): config file path string
        out_path (str): temp json file path string
        display (str): display name e.g. "ACES"
        view (str): view name e.g. "sRGB"

    Example of use:
    > pyton.exe ./ocio_wrapper.py config \
        get_display_view_colorspace_name --in_path=<path> \
        --out_path=<path> --display=<display> --view=<view>
    """

    out_data = _get_display_view_colorspace_name(in_path,
                                                 display,
                                                 view)

    with open(out_path, "w") as f:
        json.dump(out_data, f)

    print(f"Display view colorspace saved to '{out_path}'")

if __name__ == '__main__':
    main()
