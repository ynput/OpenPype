from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals
)

import os
import sys
import numbers
import copy
import collections

from Qt import QtCore
from six import text_type
import pyblish.api

root = os.path.dirname(__file__)


def get_asset(*path):
    """Return path to asset, relative the install directory

    Usage:
        >>> path = get_asset("dir", "to", "asset.png")
        >>> path == os.path.join(root, "dir", "to", "asset.png")
        True

    Arguments:
        path (str): One or more paths, to be concatenated

    """

    return os.path.join(root, *path)


def defer(delay, func):
    """Append artificial delay to `func`

    This aids in keeping the GUI responsive, but complicates logic
    when producing tests. To combat this, the environment variable ensures
    that every operation is synchonous.

    Arguments:
        delay (float): Delay multiplier; default 1, 0 means no delay
        func (callable): Any callable

    """

    delay *= float(os.getenv("PYBLISH_DELAY", 1))
    if delay > 0:
        return QtCore.QTimer.singleShot(delay, func)
    else:
        return func()


def u_print(msg, **kwargs):
    """`print` with encoded unicode.

    `print` unicode may cause UnicodeEncodeError
    or non-readable result when `PYTHONIOENCODING` is not set.
    this will fix it.

    Arguments:
        msg (unicode): Message to print.
        **kwargs: Keyword argument for `print` function.
    """

    if isinstance(msg, text_type):
        encoding = None
        try:
            encoding = os.getenv('PYTHONIOENCODING', sys.stdout.encoding)
        except AttributeError:
            # `sys.stdout.encoding` may not exists.
            pass
        msg = msg.encode(encoding or 'utf-8', 'replace')
    print(msg, **kwargs)


def collect_families_from_instances(instances, only_active=False):
    all_families = set()
    for instance in instances:
        if only_active:
            if instance.data.get("publish") is False:
                continue
        family = instance.data.get("family")
        if family:
            all_families.add(family)

        families = instance.data.get("families") or tuple()
        for family in families:
            all_families.add(family)

    return list(all_families)


class OrderGroups:
    validation_order = pyblish.api.ValidatorOrder + 0.5
    groups = collections.OrderedDict((
        (
            pyblish.api.CollectorOrder + 0.5,
            {
                "label": "Collect",
                "state": "Collecting.."
            }
        ),
        (
            pyblish.api.ValidatorOrder + 0.5,
            {
                "label": "Validate",
                "state": "Validating.."
            }
        ),
        (
            pyblish.api.ExtractorOrder + 0.5,
            {
                "label": "Extract",
                "state": "Extracting.."
            }
        ),
        (
            pyblish.api.IntegratorOrder + 0.5,
            {
                "label": "Integrate",
                "state": "Integrating.."
            }
        ),
        (
            None,
            {
                "label": "Other",
                "state": "Finishing.."
            }
        )
    ))


def env_variable_to_bool(env_key, default=False):
    """Boolean based on environment variable value."""
    # TODO: move to pype lib
    value = os.environ.get(env_key)
    if value is not None:
        value = value.lower()
        if value in ("true", "1", "yes", "on"):
            return True
        elif value in ("false", "0", "no", "off"):
            return False
    return default
