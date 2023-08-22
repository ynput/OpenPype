# -*- coding: utf-8 -*-
"""Avalon/Pyblish plugin tools."""
import os
import logging
import re

log = logging.getLogger(__name__)


def prepare_template_data(fill_pairs):
    """
        Prepares formatted data for filling template.

        It produces multiple variants of keys (key, Key, KEY) to control
        format of filled template.

        Args:
            fill_pairs (iterable) of tuples (key, value)
        Returns:
            (dict)
            ('host', 'maya') > {'host':'maya', 'Host': 'Maya', 'HOST': 'MAYA'}

    """
    fill_data = {}
    regex = re.compile(r"[a-zA-Z0-9]")
    for key, value in dict(fill_pairs).items():
        # Handle cases when value is `None` (standalone publisher)
        if value is None:
            continue
        # Keep value as it is
        fill_data[key] = value
        # Both key and value are with upper case
        fill_data[key.upper()] = value.upper()

        # Capitalize only first char of value
        # - conditions are because of possible index errors
        # - regex is to skip symbols that are not chars or numbers
        #   - e.g. "{key}" which starts with curly bracket
        capitalized = ""
        for idx in range(len(value or "")):
            char = value[idx]
            if not regex.match(char):
                capitalized += char
            else:
                capitalized += char.upper()
                capitalized += value[idx + 1:]
                break

        fill_data[key.capitalize()] = capitalized

    return fill_data


def source_hash(filepath, *args):
    """Generate simple identifier for a source file.
    This is used to identify whether a source file has previously been
    processe into the pipeline, e.g. a texture.
    The hash is based on source filepath, modification time and file size.
    This is only used to identify whether a specific source file was already
    published before from the same location with the same modification date.
    We opt to do it this way as opposed to Avalanch C4 hash as this is much
    faster and predictable enough for all our production use cases.
    Args:
        filepath (str): The source file path.
    You can specify additional arguments in the function
    to allow for specific 'processing' values to be included.
    """
    # We replace dots with comma because . cannot be a key in a pymongo dict.
    file_name = os.path.basename(filepath)
    time = str(os.path.getmtime(filepath))
    size = str(os.path.getsize(filepath))
    return "|".join([file_name, time, size] + list(args)).replace(".", ",")
