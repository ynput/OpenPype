import os
import re
import shutil
import zipfile
import collections
from pathlib import Path
from typing import Any, Optional, Iterable

# Patterns of directories to be skipped for server part of addon
IGNORE_DIR_PATTERNS: list[re.Pattern] = [
    re.compile(pattern)
    for pattern in {
        # Skip directories starting with '.'
        r"^\.",
        # Skip any pycache folders
        "^__pycache__$"
    }
]

# Patterns of files to be skipped for server part of addon
IGNORE_FILE_PATTERNS: list[re.Pattern] = [
    re.compile(pattern)
    for pattern in {
        # Skip files starting with '.'
        # NOTE this could be an issue in some cases
        r"^\.",
        # Skip '.pyc' files
        r"\.pyc$"
    }
]


def _value_match_regexes(value: str, regexes: Iterable[re.Pattern]) -> bool:
    return any(
        regex.search(value)
        for regex in regexes
    )


def find_files_in_subdir(
    src_path: str,
    ignore_file_patterns: Optional[list[re.Pattern]] = None,
    ignore_dir_patterns: Optional[list[re.Pattern]] = None
):
    """Find all files to copy in subdirectories of given path.

    All files that match any of the patterns in 'ignore_file_patterns' will
        be skipped and any directories that match any of the patterns in
        'ignore_dir_patterns' will be skipped with all subfiles.

    Args:
        src_path (str): Path to directory to search in.
        ignore_file_patterns (Optional[list[re.Pattern]]): List of regexes
            to match files to ignore.
        ignore_dir_patterns (Optional[list[re.Pattern]]): List of regexes
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


def main():
    openpype_addon_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    server_dir = openpype_addon_dir / "server"
    package_root = openpype_addon_dir / "package"
    pyproject_path = openpype_addon_dir / "pyproject.toml"

    root_dir = openpype_addon_dir.parent
    openpype_dir = root_dir / "openpype"
    version_path = openpype_dir / "version.py"

    # Read version
    version_content: dict[str, Any] = {}
    with open(str(version_path), "r") as stream:
        exec(stream.read(), version_content)
    addon_version: str = version_content["__version__"]

    output_dir = package_root / "openpype" / addon_version
    private_dir = output_dir / "private"

    # Make sure package dir is empty
    if package_root.exists():
        shutil.rmtree(str(package_root))
    # Make sure output dir is created
    output_dir.mkdir(parents=True)

    # Copy version
    shutil.copy(str(version_path), str(output_dir))
    for subitem in server_dir.iterdir():
        shutil.copy(str(subitem), str(output_dir / subitem.name))

    # Zip client
    private_dir.mkdir(parents=True)
    zip_filepath = private_dir / "client.zip"
    with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add client code content to zip
        for path, sub_path in find_files_in_subdir(str(openpype_dir)):
            zipf.write(path, f"{openpype_dir.name}/{sub_path}")

        # Add pyproject.toml
        zipf.write(str(pyproject_path), pyproject_path.name)


if __name__ == "__main__":
    main()
