"""Functions useful for delivery action or loader"""
import os
import shutil
import glob
import clique
import collections
import re


def collect_frames(files):
    """
        Returns dict of source path and its frame, if from sequence

        Uses clique as most precise solution, used when anatomy template that
        created files is not known.

        Depends that version substring starts with 'v' with any number of
        numeric characters after.

        Args:
            files(list) or (set with single value): list of source paths
        Returns:
            (dict): {'/asset/subset_v001.0001.png': '0001', ....}
    """
    collections, remainder = clique.assemble(files, minimum_items=1)

    real_file_name = None
    sources_and_frames = {}
    if len(files) == 1:
        real_file_name = list(files)[0]
        sources_and_frames[real_file_name] = None

    if collections:
        for collection in collections:
            src_head = collection.head
            src_tail = collection.tail

            # version recognized as a collection
            if re.match(".*([^a-zA-Z0-9]v%[0-9]+d).*", collection.format()):
                continue

            for index in collection.indexes:
                src_frame = collection.format("{padding}") % index
                src_file_name = "{}{}{}".format(src_head, src_frame,
                                                src_tail)
                sources_and_frames[src_file_name] = src_frame
    else:
        sources_and_frames[remainder.pop()] = None

    return sources_and_frames


def sizeof_fmt(num, suffix='B'):
    """Returns formatted string with size in appropriate unit"""
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def path_from_representation(representation, anatomy):
    from avalon import pipeline  # safer importing

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
        path = os.path.normpath(path.replace("/", "\\"))

    except KeyError:
        # Template references unavailable data
        return None

    return path


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
    """
    # Make sure path is valid for all platforms
    src_path = os.path.normpath(src_path.replace("\\", "/"))

    if not os.path.exists(src_path):
        msg = "{} doesn't exist for {}".format(src_path, repre["_id"])
        report_items["Source file was not found"].append(msg)
        return report_items, 0

    anatomy_filled = anatomy.format(anatomy_data)
    if format_dict:
        template_result = anatomy_filled["delivery"][template_name]
        delivery_path = template_result.rootless.format(**format_dict)
    else:
        delivery_path = anatomy_filled["delivery"][template_name]

    # Backwards compatibility when extension contained `.`
    delivery_path = delivery_path.replace("..", ".")
    # Make sure path is valid for all platforms
    delivery_path = os.path.normpath(delivery_path.replace("\\", "/"))

    delivery_folder = os.path.dirname(delivery_path)
    if not os.path.exists(delivery_folder):
        os.makedirs(delivery_folder)

    log.debug("Copying single: {} -> {}".format(src_path, delivery_path))
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
    src_path = os.path.normpath(src_path.replace("\\", "/"))

    def hash_path_exist(myPath):
        res = myPath.replace('#', '*')
        glob_search_results = glob.glob(res)
        if len(glob_search_results) > 0:
            return True
        return False

    if not hash_path_exist(src_path):
        msg = "{} doesn't exist for {}".format(src_path,
                                               repre["_id"])
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

    anatomy_data["frame"] = frame_indicator
    anatomy_filled = anatomy.format(anatomy_data)

    if format_dict:
        template_result = anatomy_filled["delivery"][template_name]
        delivery_path = template_result.rootless.format(**format_dict)
    else:
        delivery_path = anatomy_filled["delivery"][template_name]

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

        dst_padding = dst_collection.format("{padding}") % index
        dst = "{}{}{}".format(dst_head, dst_padding, dst_tail)
        log.debug("Copying single: {} -> {}".format(src, dst))
        copy_file(src, dst)
        uploaded += 1

    return report_items, uploaded
