"""Functions useful for delivery of published representations."""
import os
import shutil
import collections

from openpype.lib import create_hard_link


def _copy_file(src_path, dst_path):
    """Hardlink file if possible(to save space), copy if not.

    Because of using hardlinks should not be function used in other parts
    of pipeline.
    """

    if os.path.exists(dst_path):
        return
    try:
        create_hard_link(
            src_path,
            dst_path
        )
    except OSError:
        shutil.copyfile(src_path, dst_path)


def get_format_dict(anatomy, location_path):
    """Returns replaced root values from user provider value.

    Args:
        anatomy (Anatomy): Project anatomy.
        location_path (str): User provided value.

    Returns:
        (dict): Prepared data for formatting of a template.
    """

    format_dict = {}
    if not location_path:
        return format_dict

    location_path = location_path.replace("\\", "/")
    root_names = anatomy.root_names_from_templates(
        anatomy.templates["delivery"]
    )
    format_dict["root"] = {}
    for name in root_names:
        format_dict["root"][name] = location_path
    return format_dict


def check_destination_path(
    repre_id,
    anatomy,
    anatomy_data,
    datetime_data,
    template_name
):
    """ Try to create destination path based on 'template_name'.

    In the case that path cannot be filled, template contains unmatched
    keys, provide error message to filter out repre later.

    Args:
        repre_id (str): Representation id.
        anatomy (Anatomy): Project anatomy.
        anatomy_data (dict): Template data to fill anatomy templates.
        datetime_data (dict): Values with actual date.
        template_name (str): Name of template which should be used from anatomy
            templates.
    Returns:
        Dict[str, List[str]]: Report of happened errors. Key is message title
            value is detailed information.
    """

    anatomy_data.update(datetime_data)
    anatomy_filled = anatomy.format_all(anatomy_data)
    dest_path = anatomy_filled["delivery"][template_name]
    report_items = collections.defaultdict(list)

    if not dest_path.solved:
        msg = (
            "Missing keys in Representation's context"
            " for anatomy template \"{}\"."
        ).format(template_name)

        sub_msg = (
            "Representation: {}<br>"
        ).format(repre_id)

        if dest_path.missing_keys:
            keys = ", ".join(dest_path.missing_keys)
            sub_msg += (
                "- Missing keys: \"{}\"<br>"
            ).format(keys)

        if dest_path.invalid_types:
            items = []
            for key, value in dest_path.invalid_types.items():
                items.append("\"{}\" {}".format(key, str(value)))

            keys = ", ".join(items)
            sub_msg += (
                "- Invalid value DataType: \"{}\"<br>"
            ).format(keys)

        report_items[msg].append(sub_msg)

    return report_items
