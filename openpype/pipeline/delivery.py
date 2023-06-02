"""Functions useful for delivery of published representations."""
import os
import copy
import shutil
import glob
import clique
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


def deliver_single_file(
    src_path,
    repre,
    anatomy,
    template_name,
    anatomy_data,
    format_dict,
    report_items,
    log
):
    """Copy single file to calculated path based on template

    Args:
        src_path(str): path of source representation file
        repre (dict): full repre, used only in deliver_sequence, here only
            as to share same signature
        anatomy (Anatomy)
        template_name (string): user selected delivery template name
        anatomy_data (dict): data from repre to fill anatomy with
        format_dict (dict): root dictionary with names and values
        report_items (collections.defaultdict): to return error messages
        log (logging.Logger): for log printing

    Returns:
        (collections.defaultdict, int)
    """

    # Make sure path is valid for all platforms
    src_path = os.path.normpath(src_path.replace("\\", "/"))

    if not os.path.exists(src_path):
        msg = "{} doesn't exist for {}".format(src_path, repre["_id"])
        report_items["Source file was not found"].append(msg)
        return report_items, 0

    if format_dict:
        anatomy_data = copy.deepcopy(anatomy_data)
        anatomy_data["root"] = format_dict["root"]
    template_obj = anatomy.templates_obj["delivery"][template_name]
    delivery_path = template_obj.format_strict(anatomy_data)

    # Backwards compatibility when extension contained `.`
    delivery_path = delivery_path.replace("..", ".")
    # Make sure path is valid for all platforms
    delivery_path = os.path.normpath(delivery_path.replace("\\", "/"))

    delivery_folder = os.path.dirname(delivery_path)
    if not os.path.exists(delivery_folder):
        os.makedirs(delivery_folder)

    log.debug("Copying single: {} -> {}".format(src_path, delivery_path))
    _copy_file(src_path, delivery_path)

    return report_items, 1


def deliver_sequence(
    src_path,
    repre,
    anatomy,
    template_name,
    anatomy_data,
    format_dict,
    report_items,
    log,
    renumber_frame=False,
    frame_offset=0
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
        log (logging.Logger): for log printing

    Returns:
        (collections.defaultdict, int)
    """

    src_path = os.path.normpath(src_path.replace("\\", "/"))

    def hash_path_exist(myPath):
        res = myPath.replace('#', '*')
        glob_search_results = glob.glob(res)
        if len(glob_search_results) > 0:
            return True
        return False

    if not hash_path_exist(src_path):
        msg = "{} doesn't exist for {}".format(
            src_path, repre["_id"])
        report_items["Source file was not found"].append(msg)
        return report_items, 0

    delivery_templates = anatomy.templates.get("delivery") or {}
    delivery_template = delivery_templates.get(template_name)
    if delivery_template is None:
        msg = (
            "Delivery template \"{}\" in anatomy of project \"{}\""
            " was not found"
        ).format(template_name, anatomy.project_name)
        report_items[""].append(msg)
        return report_items, 0

    # Check if 'frame' key is available in template which is required
    #   for sequence delivery
    if "{frame" not in delivery_template:
        msg = (
            "Delivery template \"{}\" in anatomy of project \"{}\""
            "does not contain '{{frame}}' key to fill. Delivery of sequence"
            " can't be processed."
        ).format(template_name, anatomy.project_name)
        report_items[""].append(msg)
        return report_items, 0

    dir_path, file_name = os.path.split(str(src_path))

    context = repre["context"]
    ext = context.get("ext", context.get("representation"))

    if not ext:
        msg = "Source extension not found, cannot find collection"
        report_items[msg].append(src_path)
        log.warning("{} <{}>".format(msg, context))
        return report_items, 0

    ext = "." + ext
    # context.representation could be .psd
    ext = ext.replace("..", ".")

    src_collections, remainder = clique.assemble(os.listdir(dir_path))
    src_collection = None
    for col in src_collections:
        if col.tail != ext:
            continue

        src_collection = col
        break

    if src_collection is None:
        msg = "Source collection of files was not found"
        report_items[msg].append(src_path)
        log.warning("{} <{}>".format(msg, src_path))
        return report_items, 0

    frame_indicator = "@####@"

    anatomy_data = copy.deepcopy(anatomy_data)
    anatomy_data["frame"] = frame_indicator
    if format_dict:
        anatomy_data["root"] = format_dict["root"]
    template_obj = anatomy.templates_obj["delivery"][template_name]
    delivery_path = template_obj.format_strict(anatomy_data)

    delivery_path = os.path.normpath(delivery_path.replace("\\", "/"))
    delivery_folder = os.path.dirname(delivery_path)
    dst_head, dst_tail = delivery_path.split(frame_indicator)
    dst_padding = src_collection.padding
    dst_collection = clique.Collection(
        head=dst_head,
        tail=dst_tail,
        padding=dst_padding
    )

    if not os.path.exists(delivery_folder):
        os.makedirs(delivery_folder)

    src_head = src_collection.head
    src_tail = src_collection.tail
    uploaded = 0
    for index in src_collection.indexes:
        src_padding = src_collection.format("{padding}") % index
        src_file_name = "{}{}{}".format(src_head, src_padding, src_tail)
        src = os.path.normpath(
            os.path.join(dir_path, src_file_name)
        )

        if renumber_frame:
            first_index = src_collection.indexes[0]
            dsp_index = (int(index) - first_index) + 1
            dst_padding = dst_collection.format("{padding}") % dsp_index
            dst = "{}{}{}".format(dst_head, dst_padding, dst_tail)
            dst = os.path.normpath(
                os.path.join(delivery_folder, dst)
            )

            _copy_file(src, dst)

        else:
            dsp_index = int(index) + frame_offset
            if dsp_index < 0:
                msg = "Frame has a smaller number than Frame Offset"
                report_items[msg].append(src_file_name)
                log.warning("{} <{}>".format(msg, context))
                return report_items, 0

            dst_padding = dst_collection.format("{padding}") % dsp_index
            dst = "{}{}{}".format(dst_head, dst_padding, dst_tail)
            dst = os.path.normpath(
                os.path.join(delivery_folder, dst)
            )

            _copy_file(src, dst)

        uploaded += 1

    return report_items, uploaded
