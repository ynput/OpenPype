import os
import sys
import re
import json
import shutil
import argparse
import zipfile
import platform
import collections
from pathlib import Path
from typing import Any, Optional, Iterable, Pattern, List, Tuple


OP_ROOT_DIR = Path(__file__).parent.parent.resolve()


def read_addon_version(version_path: Path) -> str:
    """Read `__version__` attribute of a file.

    Args:
        version_path (Path): Path to a python file, which should
            contain a `__version__` variable.

    Returns:
        str: A string representation of a version, i.e. "1.0.0"
    """
    version_content: dict[str, Any] = {}
    with open(str(version_path), "r") as stream:
        exec(stream.read(), version_content)
    return version_content["__version__"]


def openpype_ignores(path, names):
    """Ignore folders when copying from OpenPype

    Certain folders are either already in AYON or split into
    addons themselves, this helper method is used by the `copytree`
    argument `ignore` to remove them.

    Args:
        path (str): A path to a directory.
        names (list[str]): The files in `path`.

    Returns:
        ignores(list): List of files names to ignore.
            They are realtive to the `path`.
    """
    openpype_dir = str(OP_ROOT_DIR / "openpype")

    ignores = []
    if path == openpype_dir:
        ignores.append("addons")
    elif path == f"{openpype_dir}/modules":
        ignores.extend(
            [
                "ftrack",
                "shotgrid",
                "sync_server",
                "example_addons",
                "slack",
                "kitsu",
            ]
        )
    elif path == f"{openpype_dir}/hosts":
        ignores.extend(["flame", "harmony"])
    elif path == f"{openpype_dir}/vendor/python/common":
        ignores.append("ayon_api")

    return ignores


def create_addon_package(
    addon_dir: Path, output_dir: Path, create_zip: bool, keep_sources: bool
):
    """Create a Rez compatible zip of an addon.

    We create a directory where we copy the files in the correct structure, and
    add a `package.py` with the correct information, then there's the option to
    create an archive or not.

    The `openpype` addon is treated differently, since most of the `client`
    data is found in the root of this project.

    Args:
        addon_dir (Path): Path to the addon.
        output_dir (Path): Path where the addon will be copied.
        create_zip (bool): Whether to make an archive of the `output_dir`.
        keep_sources (bool): Whether to wipe the `output_dir`. This is
            only used when `create_zip` is enabled.
    """
    addon_name = addon_dir.name
    openpype_dir = None

    if addon_name == "openpype":
        openpype_dir = OP_ROOT_DIR / "openpype"
        version_path = openpype_dir / "version.py"
    else:
        version_path = addon_dir / "server" / "version.py"

    addon_version = read_addon_version(version_path)

    addon_output_dir = output_dir / addon_dir.name / addon_version

    if addon_output_dir.exists():
        shutil.rmtree(str(addon_output_dir))

    addon_output_dir.mkdir(parents=True)

    shutil.copytree(
        addon_dir,
        addon_output_dir,
        ignore=shutil.ignore_patterns(
            "*.pyc",
            ".*",
            "*__pycache__*",
        ),
        dirs_exist_ok=True,
    )

    package_py = addon_output_dir / "package.py"

    with open(package_py, "w+") as pkg_py:
        pkg_py.write(
            f"""name = "{addon_dir.name}"
version = "{addon_version}"
plugin_for = ["ayon_server"]
build_command = "python {{root}}/rezbuild.py"
"""
        )

    if addon_dir.name == "openpype":
        # We get it directly from the root of the project
        shutil.copytree(
            openpype_dir,
            addon_output_dir / "client",
            ignore=openpype_ignores,
            dirs_exist_ok=True,
        )

    if create_zip:
        shutil.make_archive(
            str(output_dir / f"{addon_dir.name}-{addon_version}"),
            "zip",
            addon_output_dir,
        )

        if not keep_sources:
            shutil.rmtree(str(output_dir / addon_dir.name))


def main(
    output_dir=None,
    skip_zip=True,
    clear_output_dir=False,
    addons=None,
    keep_sources=False,
):
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    root_dir = current_dir.parent
    create_zip = not skip_zip

    if output_dir:
        output_dir = Path(output_dir)
    else:
        output_dir = current_dir / "rez_packages"

    if output_dir.exists() and clear_output_dir:
        shutil.rmtree(str(output_dir))

    output_dir.mkdir(parents=True, exist_ok=True)
    for addon_dir in current_dir.iterdir():
        if not addon_dir.is_dir():
            continue

        if addons and addon_dir.name not in addons:
            continue

        server_dir = addon_dir / "server"
        if not server_dir.exists():
            continue

        create_addon_package(addon_dir, output_dir, create_zip, keep_sources)

        print(f"- package '{addon_dir.name}' created")
    print(f"Package creation finished. Output directory: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-zip",
        dest="skip_zip",
        action="store_true",
        help=(
            "Skip zipping server package and create only" " server folder structure."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_dir",
        default=None,
        help=(
            "Directory path where package will be created"
            " (Will be purged if already exists!)"
        ),
    )
    parser.add_argument(
        "--keep-sources",
        dest="keep_sources",
        action="store_true",
        help=("Keep folder structure when server package is created."),
    )
    parser.add_argument(
        "-c",
        "--clear-output-dir",
        dest="clear_output_dir",
        action="store_true",
        help=("Clear output directory before package creation."),
    )
    parser.add_argument(
        "-a",
        "--addon",
        dest="addons",
        action="append",
        help="Limit addon creation to given addon name",
    )

    args = parser.parse_args(sys.argv[1:])
    main(
        args.output_dir,
        args.skip_zip,
        args.clear_output_dir,
        args.addons,
        args.keep_sources,
    )
