"""Functions useful for delivery action or loader"""
import os
import shutil
import functools
import warnings


class DeliveryDeprecatedWarning(DeprecationWarning):
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
            warnings.simplefilter("always", DeliveryDeprecatedWarning)
            warnings.warn(
                (
                    "Call to deprecated function '{}'"
                    "\nFunction was moved or removed.{}"
                ).format(decorated_func.__name__, warning_message),
                category=DeliveryDeprecatedWarning,
                stacklevel=4
            )
            return decorated_func(*args, **kwargs)
        return wrapper

    if func is None:
        return _decorator
    return _decorator(func)


@deprecated("openpype.lib.path_tools.collect_frames")
def collect_frames(files):
    """Returns dict of source path and its frame, if from sequence

    Uses clique as most precise solution, used when anatomy template that
    created files is not known.

    Assumption is that frames are separated by '.', negative frames are not
    allowed.

    Args:
        files(list) or (set with single value): list of source paths

    Returns:
        (dict): {'/asset/subset_v001.0001.png': '0001', ....}

    Deprecated:
        Function was moved to different location and will be removed
            after 3.16.* release.
    """

    from .path_tools import collect_frames

    return collect_frames(files)


@deprecated("openpype.lib.path_tools.format_file_size")
def sizeof_fmt(num, suffix=None):
    """Returns formatted string with size in appropriate unit

    Deprecated:
        Function was moved to different location and will be removed
            after 3.16.* release.
    """

    from .path_tools import format_file_size
    return format_file_size(num, suffix)


@deprecated("openpype.pipeline.load.get_representation_path_with_anatomy")
def path_from_representation(representation, anatomy):
    """Get representation path using representation document and anatomy.

    Args:
        representation (Dict[str, Any]): Representation document.
        anatomy (Anatomy): Project anatomy.

    Deprecated:
        Function was moved to different location and will be removed
            after 3.16.* release.
    """

    from openpype.pipeline.load import get_representation_path_with_anatomy

    return get_representation_path_with_anatomy(representation, anatomy)


@deprecated
def copy_file(src_path, dst_path):
    """Hardlink file if possible(to save space), copy if not"""
    from openpype.lib import create_hard_link  # safer importing

    if os.path.exists(dst_path):
        return
    try:
        create_hard_link(
            src_path,
            dst_path
        )
    except OSError:
        shutil.copyfile(src_path, dst_path)


@deprecated("openpype.pipeline.delivery.get_format_dict")
def get_format_dict(anatomy, location_path):
    """Returns replaced root values from user provider value.

    Args:
        anatomy (Anatomy)
        location_path (str): user provided value

    Returns:
        (dict): prepared for formatting of a template

    Deprecated:
        Function was moved to different location and will be removed
            after 3.16.* release.
    """

    from openpype.pipeline.delivery import get_format_dict

    return get_format_dict(anatomy, location_path)


@deprecated("openpype.pipeline.delivery.check_destination_path")
def check_destination_path(repre_id,
                           anatomy, anatomy_data,
                           datetime_data, template_name):
    """ Try to create destination path based on 'template_name'.

    In the case that path cannot be filled, template contains unmatched
    keys, provide error message to filter out repre later.

    Args:
        anatomy (Anatomy)
        anatomy_data (dict): context to fill anatomy
        datetime_data (dict): values with actual date
        template_name (str): to pick correct delivery template

    Returns:
        (collections.defauldict): {"TYPE_OF_ERROR":"ERROR_DETAIL"}

    Deprecated:
        Function was moved to different location and will be removed
            after 3.16.* release.
    """

    from openpype.pipeline.delivery import check_destination_path

    return check_destination_path(
        repre_id,
        anatomy,
        anatomy_data,
        datetime_data,
        template_name
    )


@deprecated("openpype.pipeline.delivery.deliver_single_file")
def process_single_file(
    src_path, repre, anatomy, template_name, anatomy_data, format_dict,
    report_items, log
):
    """Copy single file to calculated path based on template

    Args:
        src_path(str): path of source representation file
        _repre (dict): full repre, used only in process_sequence, here only
            as to share same signature
        anatomy (Anatomy)
        template_name (string): user selected delivery template name
        anatomy_data (dict): data from repre to fill anatomy with
        format_dict (dict): root dictionary with names and values
        report_items (collections.defaultdict): to return error messages
        log (Logger): for log printing

    Returns:
        (collections.defaultdict , int)

    Deprecated:
        Function was moved to different location and will be removed
            after 3.16.* release.
    """

    from openpype.pipeline.delivery import deliver_single_file

    return deliver_single_file(
        src_path, repre, anatomy, template_name, anatomy_data, format_dict,
        report_items, log
    )


@deprecated("openpype.pipeline.delivery.deliver_sequence")
def process_sequence(
    src_path, repre, anatomy, template_name, anatomy_data, format_dict,
    report_items, log
):
    """ For Pype2(mainly - works in 3 too) where representation might not
        contain files.

    Uses listing physical files (not 'files' on repre as a)might not be
     present, b)might not be reliable for representation and copying them.

     TODO Should be refactored when files are sufficient to drive all
     representations.

    Args:
        src_path(str): path of source representation file
        repre (dict): full representation
        anatomy (Anatomy)
        template_name (string): user selected delivery template name
        anatomy_data (dict): data from repre to fill anatomy with
        format_dict (dict): root dictionary with names and values
        report_items (collections.defaultdict): to return error messages
        log (Logger): for log printing

    Returns:
        (collections.defaultdict , int)

    Deprecated:
        Function was moved to different location and will be removed
            after 3.16.* release.
    """

    from openpype.pipeline.delivery import deliver_sequence

    return deliver_sequence(
        src_path, repre, anatomy, template_name, anatomy_data, format_dict,
        report_items, log
    )
