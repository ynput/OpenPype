# -*- coding: utf-8 -*-
"""Script to rehash and repack current version."""
from igniter import bootstrap_repos
import enlighten
import blessed
from pathlib import Path
import os
from zipfile import ZipFile, BadZipFile
from igniter.bootstrap_repos import sha256sum


term = blessed.Terminal()
manager = enlighten.get_manager()
last_increment = 0

progress_bar = enlighten.Counter(
        total=100, desc="OpenPype ZIP", units="%", color="green")



zip_path = Path(version_path).parent


with ZipFile(zip_path, "w") as zip_file:
    progress = 0
    openpype_root = openpype_path.resolve()
    # generate list of filtered paths
    dir_filter = [openpype_root / f for f in self.openpype_filter]
    checksums = []

    file: Path
    for file in openpype_list:
        progress += openpype_inc
        self._progress_callback(int(progress))

        # if file resides in filtered path, skip it
        is_inside = None
        df: Path
        for df in dir_filter:
            try:
                is_inside = file.resolve().relative_to(df)
            except ValueError:
                pass

        if not is_inside:
            continue

        processed_path = file
        self._print(f"- processing {processed_path}")

        checksums.append(
            (
                sha256sum(file.as_posix()),
                file.resolve().relative_to(openpype_root)
            )
        )
        zip_file.write(
            file, file.resolve().relative_to(openpype_root))

    checksums_str = ""
    for c in checksums:
        checksums_str += "{}:{}\n".format(c[0], c[1])
    zip_file.writestr("checksums", checksums_str)
    # test if zip is ok
    zip_file.testzip()
    self._progress_callback(100)
