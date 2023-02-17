# -*- coding: utf-8 -*-
"""Avalon/Pyblish plugin tools."""
import os
import logging
import re

import warnings
import functools

from openpype.client import get_asset_by_id

log = logging.getLogger(__name__)


class PluginToolsDeprecatedWarning(DeprecationWarning):
    pass


def deprecated(new_destination):
    """Mark functions as deprecated.

    It will result in a warning being emitted when the function is used.
    """

    func = None
    if callable(new_destination):
        func = new_destination
        new_destination = None

    def _decorator(decorated_func):
        if new_destination is None:
            warning_message = (
                " Please check content of deprecated function to figure out"
                " possible replacement."
            )
        else:
            warning_message = " Please replace your usage with '{}'.".format(
                new_destination
            )

        @functools.wraps(decorated_func)
        def wrapper(*args, **kwargs):
            warnings.simplefilter("always", PluginToolsDeprecatedWarning)
            warnings.warn(
                (
                    "Call to deprecated function '{}'"
                    "\nFunction was moved or removed.{}"
                ).format(decorated_func.__name__, warning_message),
                category=PluginToolsDeprecatedWarning,
                stacklevel=4
            )
            return decorated_func(*args, **kwargs)
        return wrapper

    if func is None:
        return _decorator
    return _decorator(func)


@deprecated("openpype.pipeline.create.TaskNotSetError")
def TaskNotSetError(*args, **kwargs):
    from openpype.pipeline.create import TaskNotSetError

    return TaskNotSetError(*args, **kwargs)


@deprecated("openpype.pipeline.create.get_subset_name")
def get_subset_name_with_asset_doc(
    family,
    variant,
    task_name,
    asset_doc,
    project_name=None,
    host_name=None,
    default_template=None,
    dynamic_data=None
):
    """Calculate subset name based on passed context and OpenPype settings.

    Subst name templates are defined in `project_settings/global/tools/creator
    /subset_name_profiles` where are profiles with host name, family, task name
    and task type filters. If context does not match any profile then
    `DEFAULT_SUBSET_TEMPLATE` is used as default template.

    That's main reason why so many arguments are required to calculate subset
    name.

    Args:
        family (str): Instance family.
        variant (str): In most of cases it is user input during creation.
        task_name (str): Task name on which context is instance created.
        asset_doc (dict): Queried asset document with it's tasks in data.
            Used to get task type.
        project_name (str): Name of project on which is instance created.
            Important for project settings that are loaded.
        host_name (str): One of filtering criteria for template profile
            filters.
        default_template (str): Default template if any profile does not match
            passed context. Constant 'DEFAULT_SUBSET_TEMPLATE' is used if
            is not passed.
        dynamic_data (dict): Dynamic data specific for a creator which creates
            instance.
    """

    from openpype.pipeline.create import get_subset_name

    return get_subset_name(
        family,
        variant,
        task_name,
        asset_doc,
        project_name,
        host_name,
        default_template,
        dynamic_data
    )


@deprecated
def get_subset_name(
    family,
    variant,
    task_name,
    asset_id,
    project_name=None,
    host_name=None,
    default_template=None,
    dynamic_data=None,
    dbcon=None
):
    """Calculate subset name using OpenPype settings.

    This variant of function expects asset id as argument.

    This is legacy function should be replaced with
    `get_subset_name_with_asset_doc` where asset document is expected.
    """

    from openpype.pipeline.create import get_subset_name

    if project_name is None:
        project_name = dbcon.project_name

    asset_doc = get_asset_by_id(project_name, asset_id, fields=["data.tasks"])

    return get_subset_name(
        family,
        variant,
        task_name,
        asset_doc,
        project_name,
        host_name,
        default_template,
        dynamic_data
    )


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
