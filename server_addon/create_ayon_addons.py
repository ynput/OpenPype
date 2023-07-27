import os
import sys
import re
import json
import shutil
import zipfile
import platform
import collections
from pathlib import Path
from typing import Any, Optional, Iterable, Pattern

# Patterns of directories to be skipped for server part of addon
IGNORE_DIR_PATTERNS: list[Pattern] = [
    re.compile(pattern)
    for pattern in {
        # Skip directories starting with '.'
        r"^\.",
        # Skip any pycache folders
        "^__pycache__$"
    }
]

# Patterns of files to be skipped for server part of addon
IGNORE_FILE_PATTERNS: list[Pattern] = [
    re.compile(pattern)
    for pattern in {
        # Skip files starting with '.'
        # NOTE this could be an issue in some cases
        r"^\.",
        # Skip '.pyc' files
        r"\.pyc$"
    }
]


class ZipFileLongPaths(zipfile.ZipFile):
    """Allows longer paths in zip files.

    Regular DOS paths are limited to MAX_PATH (260) characters, including
    the string's terminating NUL character.
    That limit can be exceeded by using an extended-length path that
    starts with the '\\?\' prefix.
    """
    _is_windows = platform.system().lower() == "windows"

    def _extract_member(self, member, tpath, pwd):
        if self._is_windows:
            tpath = os.path.abspath(tpath)
            if tpath.startswith("\\\\"):
                tpath = "\\\\?\\UNC\\" + tpath[2:]
            else:
                tpath = "\\\\?\\" + tpath

        return super(ZipFileLongPaths, self)._extract_member(
            member, tpath, pwd
        )


def _value_match_regexes(value: str, regexes: Iterable[Pattern]) -> bool:
    return any(
        regex.search(value)
        for regex in regexes
    )


def find_files_in_subdir(
    src_path: str,
    ignore_file_patterns: Optional[list[Pattern]] = None,
    ignore_dir_patterns: Optional[list[Pattern]] = None,
):
    """Find all files to copy in subdirectories of given path.

    All files that match any of the patterns in 'ignore_file_patterns' will
        be skipped and any directories that match any of the patterns in
        'ignore_dir_patterns' will be skipped with all subfiles.

    Args:
        src_path (str): Path to directory to search in.
        ignore_file_patterns (Optional[list[Pattern]]): List of regexes
            to match files to ignore.
        ignore_dir_patterns (Optional[list[Pattern]]): List of regexes
            to match directories to ignore.

    Returns:
        list[tuple[str, str]]: List of tuples with path to file and parent
            directories relative to 'src_path'.
    """

    if ignore_file_patterns is None:
        ignore_file_patterns = IGNORE_FILE_PATTERNS

    if ignore_dir_patterns is None:
        ignore_dir_patterns = IGNORE_DIR_PATTERNS
    output: list[tuple[str, str]] = []

    hierarchy_queue = collections.deque()
    hierarchy_queue.append((src_path, []))
    while hierarchy_queue:
        item: tuple[str, str] = hierarchy_queue.popleft()
        dirpath, parents = item
        for name in os.listdir(dirpath):
            path = os.path.join(dirpath, name)
            if os.path.isfile(path):
                if not _value_match_regexes(name, ignore_file_patterns):
                    items = list(parents)
                    items.append(name)
                    output.append((path, os.path.sep.join(items)))
                continue

            if not _value_match_regexes(name, ignore_dir_patterns):
                items = list(parents)
                items.append(name)
                hierarchy_queue.append((path, items))

    return output


def read_addon_version(version_path: Path) -> str:
    # Read version
    version_content: dict[str, Any] = {}
    with open(str(version_path), "r") as stream:
        exec(stream.read(), version_content)
    return version_content["__version__"]


def get_addon_version(addon_dir: Path) -> str:
    return read_addon_version(addon_dir / "server" / "version.py")


def create_addon_zip(
    output_dir: Path,
    addon_name: str,
    addon_version: str,
    keep_source: bool
):
    zip_filepath = output_dir / f"{addon_name}-{addon_version}.zip"
    addon_output_dir = output_dir / addon_name / addon_version
    with ZipFileLongPaths(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr(
            "manifest.json",
            json.dumps({
                "addon_name": addon_name,
                "addon_version": addon_version
            })
        )
        # Add client code content to zip
        src_root = os.path.normpath(str(addon_output_dir.absolute()))
        src_root_offset = len(src_root) + 1
        for root, _, filenames in os.walk(str(addon_output_dir)):
            rel_root = ""
            if root != src_root:
                rel_root = root[src_root_offset:]

            for filename in filenames:
                src_path = os.path.join(root, filename)
                if rel_root:
                    dst_path = os.path.join("addon", rel_root, filename)
                else:
                    dst_path = os.path.join("addon", filename)
                zipf.write(src_path, dst_path)

    if not keep_source:
        shutil.rmtree(str(output_dir / addon_name))


def create_openpype_package(
    addon_dir: Path,
    output_dir: Path,
    root_dir: Path,
    create_zip: bool,
    keep_source: bool
):
    server_dir = addon_dir / "server"
    pyproject_path = addon_dir / "client" / "pyproject.toml"

    openpype_dir = root_dir / "openpype"
    version_path = openpype_dir / "version.py"
    addon_version = read_addon_version(version_path)

    addon_output_dir = output_dir / "openpype" / addon_version
    private_dir = addon_output_dir / "private"
    # Make sure dir exists
    addon_output_dir.mkdir(parents=True)
    private_dir.mkdir(parents=True)

    # Copy version
    shutil.copy(str(version_path), str(addon_output_dir))
    for subitem in server_dir.iterdir():
        shutil.copy(str(subitem), str(addon_output_dir / subitem.name))

    # Copy pyproject.toml
    shutil.copy(
        str(pyproject_path),
        (private_dir / pyproject_path.name)
    )

    # Zip client
    zip_filepath = private_dir / "client.zip"
    with ZipFileLongPaths(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add client code content to zip
        for path, sub_path in find_files_in_subdir(str(openpype_dir)):
            zipf.write(path, f"{openpype_dir.name}/{sub_path}")

    if create_zip:
        create_addon_zip(output_dir, "openpype", addon_version, keep_source)


def create_addon_package(
    addon_dir: Path,
    output_dir: Path,
    create_zip: bool,
    keep_source: bool
):
    server_dir = addon_dir / "server"
    addon_version = get_addon_version(addon_dir)

    addon_output_dir = output_dir / addon_dir.name / addon_version
    if addon_output_dir.exists():
        shutil.rmtree(str(addon_output_dir))
    addon_output_dir.mkdir(parents=True)

    # Copy server content
    src_root = os.path.normpath(str(server_dir.absolute()))
    src_root_offset = len(src_root) + 1
    for root, _, filenames in os.walk(str(server_dir)):
        dst_root = addon_output_dir
        if root != src_root:
            rel_root = root[src_root_offset:]
            dst_root = dst_root / rel_root

        dst_root.mkdir(parents=True, exist_ok=True)
        for filename in filenames:
            src_path = os.path.join(root, filename)
            shutil.copy(src_path, str(dst_root))

    if create_zip:
        create_addon_zip(
            output_dir, addon_dir.name, addon_version, keep_source
        )


def main(create_zip=True, keep_source=False):
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    root_dir = current_dir.parent
    output_dir = current_dir / "packages"
    print("Package creation started...")

    # Make sure package dir is empty
    if output_dir.exists():
        shutil.rmtree(str(output_dir))
    # Make sure output dir is created
    output_dir.mkdir(parents=True)

    for addon_dir in current_dir.iterdir():
        if not addon_dir.is_dir():
            continue

        server_dir = addon_dir / "server"
        if not server_dir.exists():
            continue

        if addon_dir.name == "openpype":
            create_openpype_package(
                addon_dir, output_dir, root_dir, create_zip, keep_source
            )

        else:
            create_addon_package(
                addon_dir, output_dir, create_zip, keep_source
            )

        print(f"- package '{addon_dir.name}' created")
    print(f"Package creation finished. Output directory: {output_dir}")


if __name__ == "__main__":
    create_zip = "--skip-zip" not in sys.argv
    keep_sources = "--keep-sources" in sys.argv
    main(create_zip, keep_sources)
