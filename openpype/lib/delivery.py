"""Functions useful for delivery action or loader"""
import os
from avalon import pipeline
from avalon.vendor import filelink
import shutil
import clique
import collections


def sizeof_fmt(num, suffix='B'):
    """Returns formatted string with size in appropriate unit"""
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def path_from_represenation(representation, anatomy):
    try:
        template = representation["data"]["template"]

    except KeyError:
        return None

    try:
        context = representation["context"]
        context["root"] = anatomy.roots
        path = pipeline.format_template_with_optional_keys(
            context, template
        )

    except KeyError:
        # Template references unavailable data
        return None

    return os.path.normpath(path)


def copy_file(src_path, dst_path):
    """Hardlink file if possible(to save space), copy if not"""
    if os.path.exists(dst_path):
        return
    try:
        filelink.create(
            src_path,
            dst_path,
            filelink.HARDLINK
        )
    except OSError:
        shutil.copyfile(src_path, dst_path)


def get_format_dict(anatomy, location_path):
    """Returns replaced root values from user provider value.

        Args:
            anatomy (Anatomy)
            location_path (str): user provided value
        Returns:
            (dict): prepared for formatting of a template
    """
    format_dict = {}
    if location_path:
        location_path = location_path.replace("\\", "/")
        root_names = anatomy.root_names_from_templates(
            anatomy.templates["delivery"]
        )
        if root_names is None:
            format_dict["root"] = location_path
        else:
            format_dict["root"] = {}
            for name in root_names:
                format_dict["root"][name] = location_path
    return format_dict


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
    """
    anatomy_data.update(datetime_data)
    anatomy_filled = anatomy.format_all(anatomy_data)
    dest_path = anatomy_filled["delivery"][template_name]
    report_items = collections.defaultdict(list)
    sub_msg = None
    if not dest_path.solved:
        msg = (
            "Missing keys in Representation's context"
            " for anatomy template \"{}\"."
        ).format(template_name)

        if dest_path.missing_keys:
            keys = ", ".join(dest_path.missing_keys)
            sub_msg = (
                "Representation: {}<br>- Missing keys: \"{}\"<br>"
            ).format(repre_id, keys)

        if dest_path.invalid_types:
            items = []
            for key, value in dest_path.invalid_types.items():
                items.append("\"{}\" {}".format(key, str(value)))

            keys = ", ".join(items)
            sub_msg = (
                "Representation: {}<br>"
                "- Invalid value DataType: \"{}\"<br>"
            ).format(repre_id, keys)

        report_items[msg].append(sub_msg)

    return report_items


def process_single_file(
    src_path, _repre, anatomy, template_name, anatomy_data, format_dict,
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
    """
    anatomy_filled = anatomy.format(anatomy_data)
    if format_dict:
        template_result = anatomy_filled["delivery"][template_name]
        delivery_path = template_result.rootless.format(**format_dict)
    else:
        delivery_path = anatomy_filled["delivery"][template_name]

    delivery_folder = os.path.dirname(delivery_path)
    if not os.path.exists(delivery_folder):
        os.makedirs(delivery_folder)

    log.debug("Copying single: {} -> {}".format(src_path, delivery_path))
    print("Copying single: {} -> {}".format(src_path, delivery_path))
    copy_file(src_path, delivery_path)

    return report_items, 1


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
    """
    dir_path, file_name = os.path.split(str(src_path))

    context = repre["context"]
    ext = context.get("ext", context.get("representation"))

    if not ext:
        msg = "Source extension not found, cannot find collection"
        report_items[msg].append(src_path)
        log.warning("{} <{}>".format(msg, context))
        return report_items, 0

    ext = "." + ext

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

    anatomy_data["frame"] = frame_indicator
    anatomy_filled = anatomy.format(anatomy_data)

    if format_dict:
        template_result = anatomy_filled["delivery"][template_name]
        delivery_path = template_result.rootless.format(**format_dict)
    else:
        delivery_path = anatomy_filled["delivery"][template_name]

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

        dst_padding = dst_collection.format("{padding}") % index
        dst = "{}{}{}".format(dst_head, dst_padding, dst_tail)
        log.debug("Copying single: {} -> {}".format(src, dst))
        copy_file(src, dst)
        uploaded += 1

    return report_items, uploaded


def report(report_items):
    """Returns dict with final status of delivery (succes, fail etc.)."""
    items = []
    title = "Delivery report"
    for msg, _items in report_items.items():
        if not _items:
            continue

        if items:
            items.append({"type": "label", "value": "---"})

        items.append({
            "type": "label",
            "value": "# {}".format(msg)
        })
        if not isinstance(_items, (list, tuple)):
            _items = [_items]
        __items = []
        for item in _items:
            __items.append(str(item))

        items.append({
            "type": "label",
            "value": '<p>{}</p>'.format("<br>".join(__items))
        })

    if not items:
        return {
            "success": True,
            "message": "Delivery Finished"
        }

    return {
        "items": items,
        "title": title,
        "success": False,
        "message": "Delivery Finished"
    }
