# -*- coding: utf-8 -*-
"""Tools for working with viewport in Maya."""
import contextlib
from maya import cmds  # noqa


@contextlib.contextmanager
def vp2_paused_context():
    """Context manager to stop updating of vp2 viewport."""
    state = cmds.ogs(pause=True, query=True)

    if not state:
        cmds.ogs(pause=True)

    try:
        yield
    finally:
        if cmds.ogs(pause=True, query=True) != state:
            cmds.ogs(pause=True)
