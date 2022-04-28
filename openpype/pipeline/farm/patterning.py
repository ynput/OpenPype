# -*- coding: utf-8 -*-
import re


def match_aov_pattern(host_name, aov_patterns, render_file_name):
    """Matching against a `AOV` pattern in the render files.

    In order to match the AOV name we must compare
    against the render filename string that we are
    grabbing the render filename string  from the collection
    that we have grabbed from `exp_files`.

    Args:
        app (str): Host name.
        aov_patterns (dict):  AOV patterns from AOV filters.
        render_file_name (str): Incoming file name to match against.

    Returns:
        bool: Review state for rendered file (render_file_name).
    """
    aov_pattern = aov_patterns.get(host_name, [])
    if not aov_pattern:
        return False
    return any(re.match(p, render_file_name) for p in aov_pattern)
