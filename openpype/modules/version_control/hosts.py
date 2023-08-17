from __future__ import annotations

import functools

from . import api

_typing = False
if _typing:
    from typing import Any
    from typing import Callable


def pre_save(function: Callable[..., Any]):
    """
    Decorator wrapping a hosts `workio.save_file` function,
    checking out the file being saved if version control
    is active.
    """

    @functools.wraps(function)
    def wrapper(*args: Any, **kwargs: Any):
        if api.is_version_control_enabled():
            api.checkout(args[0])

        return function(*args, **kwargs)

    return wrapper


def pre_load(function: Callable[..., Any]):
    """
    Decorator wrapping a hosts `workio.save_file` function,
    checking out the file being saved if version control
    is active.
    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        if api.is_version_control_enabled():
            api.sync_latest_version(args[0])

        return function(*args, **kwargs)

    return wrapper
