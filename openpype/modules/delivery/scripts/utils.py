import clique
import re
import glob
import datetime
import getpass
import os
import requests
import fileseq

from openpype.lib import Logger, is_running_from_build
from openpype.pipeline import Anatomy
from openpype.pipeline.colorspace import get_imageio_config


logger = Logger.get_logger(__name__)

# Regular expression that allows us to replace the frame numbers of a file path
# with any string token
# RE_FRAME_NUMBER = re.compile("(?P<prefix>.*?)(?P<frame>(?<=[_\.])\d+(?=[_\.]))\.(?P<extension>\w+\.?(?:sc|gz)?)$")

# rewritten to remove leading _ or . requirement to catch patterns like marshall0001.png
# RE_FRAME_NUMBER = re.compile("(?P<prefix>.*?)(?P<frame>\d+)\.(?P<extension>\w+\.?(?:sc|gz)?)$")
RE_FRAME_NUMBER = re.compile(r"(?P<prefix>.*?)(?P<frame>\d+)\.(?P<extension>\w+\.?(?:sc|gz)?)$")

# previous RE:   r"(?P<prefix>^(.*)+)\.(?P<frame>\d+)\.(?P<extension>\w+\.?(sc|gz)?$)"

def create_metadata_path(instance_data):
    # Ensure output dir exists
    output_dir = instance_data.get(
        "publishRenderMetadataFolder", instance_data["outputDir"]
    )

    try:
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
    except OSError:
        # directory is not available
        logger.warning("Path is unreachable: `{}`".format(output_dir))

    metadata_filename = "{}_{}_{}_metadata.json".format(
        datetime.datetime.now().strftime("%d%m%Y%H%M%S"),
        instance_data["asset"],
        instance_data["subset"]
    )

    return os.path.join(output_dir, metadata_filename)


# def replace_frame_number_with_token(path, token):
#     result = RE_FRAME_NUMBER.sub(
#         r"\g<prefix>.{}.\g<extension>".format(token), path
#     )
#     return result
def replace_frame_number_with_token(path, token):
    result = RE_FRAME_NUMBER.sub(
        r"\g<prefix>{}.\g<extension>".format(token), path)
    return result


def get_representations(
    instance_data,
    exp_representations,
    add_review=True,
    publish_to_sg=False
):
    """Create representations for file sequences.

    This will return representation dictionaries of expected files. There
    should be only one sequence of files for most cases, but if not - we create
    a representation for each.

    If the file path given is just a frame, it

    Arguments:
        instance_data (dict): instance["data"] for which we are
                            setting representations
        exp_representations (dict[str:str]): Dictionary of expected
            representations that should be created. Key is name of
            representation and value is a file path to one of the files
            from the representation (i.e., "exr": "/path/to/beauty.1001.exr").

    Returns:
        list of representations

    """
    logger.info("Searching representations...")

    anatomy = Anatomy(instance_data["project"])
    representations = []

    for rep_name, file_path in exp_representations.items():
        rep_frame_start = None
        rep_frame_end = None
        ext = None
        # Convert file path so it can be used with glob and find all the
        # frames for the sequence
        # print(file_path)
        file_pattern = replace_frame_number_with_token(file_path, "*")
        representation_files = glob.glob(file_pattern)
        # print(file_pattern, representation_files)
        logger.info(representation_files)
        collections, remainder = clique.assemble(representation_files)

        # print(collections, remainder)
        # If file path is in remainder it means it was a single file
        if file_path in remainder:
            collections = [remainder]
            frame_match = RE_FRAME_NUMBER.match(file_path)
            if frame_match:
                ext = frame_match.group("extension")
                frame = frame_match.group("frame")
                rep_frame_start = frame
                rep_frame_end = frame
            else:
                rep_frame_start = 1
                rep_frame_end = 1
                ext = os.path.splitext(file_path)[1][1:]

        elif not collections:
            logger.warning(
                "Couldn't find a collection for file pattern '%s'.",
                file_pattern
            )
            continue
        if len(collections) > 1:
            logger.warning(
                "More than one sequence find for the file pattern '%s'."
                " Using only first one: %s",
                file_pattern,
                collections,
            )
        collection = collections[0]

        if not ext:
            ext = collection.tail.lstrip(".")

        staging = os.path.dirname(list(collection)[0])
        success, rootless_staging_dir = anatomy.find_root_template_from_path(
            staging
        )
        if success:
            staging = rootless_staging_dir
        else:
            logger.warning(
                "Could not find root path for remapping '%s'."
                " This may cause issues on farm.",
                staging
            )

        if not rep_frame_start or not rep_frame_end:
            col_frame_range = list(collection.indexes)
            rep_frame_start = col_frame_range[0]
            rep_frame_end = col_frame_range[-1]

        tags = []
        if add_review:
            tags.append("review")

        if publish_to_sg:
            tags.append("shotgridreview")

        files = [os.path.basename(f) for f in list(collection)]
        # If it's a single file on the collection we remove it
        # from the list as OP checks if "files" is a list or tuple
        # at certain places to validate if it's a sequence or not
        if len(files) == 1:
            files = files[0]

        rep = {
            "name": rep_name,
            "ext": ext,
            "files": files,
            "frameStart": rep_frame_start,
            "frameEnd": rep_frame_end,
            # If expectedFile are absolute, we need only filenames
            "stagingDir": staging,
            "fps": instance_data.get("fps"),
            "tags": tags,
        }

        if instance_data.get("multipartExr", False):
            rep["tags"].append("multipartExr")

        # support conversion from tiled to scanline
        if instance_data.get("convertToScanline"):
            logger.info("Adding scanline conversion.")
            rep["tags"].append("toScanline")

        representations.append(rep)

        solve_families(instance_data, add_review)
    print(8)

    return representations

# def get_representations_2(
#     instance_data,
#     exp_representations,
#     add_review=True,
#     publish_to_sg=False
# ):
#     """Create representations for file sequences.

#     This will return representation dictionaries of expected files. There
#     should be only one sequence of files for most cases, but if not - we create
#     a representation for each.

#     If the file path given is just a frame, it

#     Arguments:
#         instance_data (dict): instance["data"] for which we are
#                             setting representations
#         # exp_representations (dict[str:str]): Dictionary of expected
#         #     representations that should be created. Key is name of
#         #     representation and value is a file path to one of the files
#         #     from the representation (i.e., "exr": "/path/to/beauty.1001.exr").

#         v2 exp_representations dict[str:fileseq] dictionary of expected representations to be created.
#         Key is name of representation and value is a fileseq object.

#     Returns:
#         list of representations

#     """
#     anatomy = Anatomy(instance_data["project"])
#     representations = []

#     for rep_name, file_seq in exp_representations.items():
#         rep_frame_start = None
#         rep_frame_end = None
#         ext = None
#         # Convert file path so it can be used with glob and find all the
#         # frames for the sequence
#         # print(file_path)
#         file_pattern = replace_frame_number_with_token(file_path, "*")
#         representation_files = glob.glob(file_pattern)
#         # print(file_pattern, representation_files)
#         collections, remainder = clique.assemble(representation_files)

#         # print(collections, remainder)
#         # If file path is in remainder it means it was a single file
#         if file_path in remainder:
#             collections = [remainder]
#             frame_match = RE_FRAME_NUMBER.match(file_path)
#             if frame_match:
#                 ext = frame_match.group("extension")
#                 frame = frame_match.group("frame")
#                 rep_frame_start = frame
#                 rep_frame_end = frame
#             else:
#                 rep_frame_start = 1
#                 rep_frame_end = 1
#                 ext = os.path.splitext(file_path)[1][1:]

#         elif not collections:
#             logger.warning(
#                 "Couldn't find a collection for file pattern '%s'.",
#                 file_pattern
#             )
#             continue
#         if len(collections) > 1:
#             logger.warning(
#                 "More than one sequence find for the file pattern '%s'."
#                 " Using only first one: %s",
#                 file_pattern,
#                 collections,
#             )
#         collection = collections[0]

#         if not ext:
#             ext = collection.tail.lstrip(".")

#         staging = os.path.dirname(list(collection)[0])
#         success, rootless_staging_dir = anatomy.find_root_template_from_path(
#             staging
#         )
#         if success:
#             staging = rootless_staging_dir
#         else:
#             logger.warning(
#                 "Could not find root path for remapping '%s'."
#                 " This may cause issues on farm.",
#                 staging
#             )

#         if not rep_frame_start or not rep_frame_end:
#             col_frame_range = list(collection.indexes)
#             rep_frame_start = col_frame_range[0]
#             rep_frame_end = col_frame_range[-1]

#         tags = []
#         if add_review:
#             tags.append("review")

#         if publish_to_sg:
#             tags.append("shotgridreview")

#         files = [os.path.basename(f) for f in list(collection)]
#         # If it's a single file on the collection we remove it
#         # from the list as OP checks if "files" is a list or tuple
#         # at certain places to validate if it's a sequence or not
#         if len(files) == 1:
#             files = files[0]

#         rep = {
#             "name": rep_name,
#             "ext": ext,
#             "files": files,
#             "frameStart": rep_frame_start,
#             "frameEnd": rep_frame_end,
#             # If expectedFile are absolute, we need only filenames
#             "stagingDir": staging,
#             "fps": instance_data.get("fps"),
#             "tags": tags,
#         }

#         if instance_data.get("multipartExr", False):
#             rep["tags"].append("multipartExr")

#         # support conversion from tiled to scanline
#         if instance_data.get("convertToScanline"):
#             logger.info("Adding scanline conversion.")
#             rep["tags"].append("toScanline")

#         representations.append(rep)

#         solve_families(instance_data, add_review)
#     print(8)

#     return representations


def get_colorspace_settings(project_name):
    """Returns colorspace settings for project.

    Returns:
        tuple | bool: config, file rules or None
    """
    config_data = get_imageio_config(
        project_name,
        host_name="nuke",  # temporary hack as get_imageio_config doesn't support grabbing just global
    )

    # in case host color management is not enabled
    if not config_data:
        return None

    return config_data


def set_representation_colorspace(
    representation,
    project_name,
    colorspace=None,
):
    """Sets colorspace data to representation.

    Args:
        representation (dict): publishing representation
        project_name (str): Name of project
        config_data (dict): host resolved config data
        file_rules (dict): host resolved file rules data
        colorspace (str, optional): colorspace name. Defaults to None.

    Example:
        ```
        {
            # for other publish plugins and loaders
            "colorspace": "linear",
            "config": {
                # for future references in case need
                "path": "/abs/path/to/config.ocio",
                # for other plugins within remote publish cases
                "template": "{project[root]}/path/to/config.ocio"
            }
        }
        ```

    """
    ext = representation["ext"]
    # check extension
    logger.debug("__ ext: `{}`".format(ext))

    config_data = get_colorspace_settings(project_name)

    if not config_data:
        # warn in case no colorspace path was defined
        logger.warning("No colorspace management was defined")
        return

    logger.debug("Config data is: `{}`".format(config_data))

    # infuse data to representation
    if colorspace:
        colorspace_data = {"colorspace": colorspace, "config": config_data}

        # update data key
        representation["colorspaceData"] = colorspace_data


def solve_families(instance_data, preview=False):
    families = instance_data.get("families")

    # if we have one representation with preview tag
    # flag whole instance_data for review and for ftrack
    if preview:
        if "review" not in families:
            logger.debug('Adding "review" to families because of preview tag.')
            families.append("review")
        instance_data["families"] = families


def get_possible_representations(
    instance_data,
    exp_representations,
    add_review=True,
    publish_to_sg=False
):
    """
    Create representations for file sequences that may not exists, for example
    from a Deadline Job.

    This will return representation dictionaries of expected files. There
    should be only one sequence of files for most cases, but if not - we create
    a representation for each.

    If the file path given is just a frame, it

    Arguments:
        instance_data (dict): instance["data"] for which we are
                            setting representations
        exp_representations (dict[str:str]): Dictionary of expected
            representations that should be created. Key is name of
            representation and value is a file path to one of the files
            from the representation (i.e., "exr": "/path/to/beauty.1001.exr").

    Returns:
        list of representations

    """
    logger.info("Generating possible representations...")
    anatomy = Anatomy(instance_data["project"])
    representations = []

    for rep_name, file_path in exp_representations.items():
        # file_path is defined like: '</path/to/image.<frame_in>-<frame_out>#.ext>'
        # as expected by fileseq.
        logger.info(f"Expanding: {file_path}")

        sequence = fileseq.FileSequence(file_path,
                                        pad_style=fileseq.PAD_STYLE_HASH4)
        file_path = sequence.format(
            template='{dirname}{basename}{padding}{extension}')

        rep_frame_start = sequence.start()
        rep_frame_end = sequence.end()

        ext = None
        representation_files = [sequence[idx] for idx, fr in
                                enumerate(sequence.frameSet())]

        collections, remainder = clique.assemble(representation_files)

        # If file path is in remainder it means it was a single file
        if file_path in remainder:
            collections = [remainder]
            frame_match = RE_FRAME_NUMBER.match(file_path)
            if frame_match:
                ext = frame_match.group("extension")
                frame = frame_match.group("frame")
                rep_frame_start = frame
                rep_frame_end = frame
            else:
                rep_frame_start = 1
                rep_frame_end = 1
                ext = os.path.splitext(file_path)[1][1:]

        elif not collections:
            logger.warning(
                "Couldn't find a collection for file pattern '%s'.",
                file_path
            )
            continue
        if len(collections) > 1:
            logger.warning(
                "More than one sequence find for the file pattern '%s'."
                " Using only first one: %s",
                file_path,
                collections,
            )
        collection = collections[0]

        if not ext:
            ext = collection.tail.lstrip(".")

        staging = os.path.dirname(list(collection)[0])
        success, rootless_staging_dir = anatomy.find_root_template_from_path(
            staging
        )
        if success:
            staging = rootless_staging_dir
        else:
            logger.warning(
                "Could not find root path for remapping '%s'."
                " This may cause issues on farm.",
                staging
            )

        if not rep_frame_start or not rep_frame_end:
            col_frame_range = list(collection.indexes)
            rep_frame_start = col_frame_range[0]
            rep_frame_end = col_frame_range[-1]

        tags = []
        if add_review:
            tags.append("review")

        if publish_to_sg:
            tags.append("shotgridreview")

        files = [os.path.basename(f) for f in list(collection)]
        # If it's a single file on the collection we remove it
        # from the list as OP checks if "files" is a list or tuple
        # at certain places to validate if it's a sequence or not
        if len(files) == 1:
            files = files[0]

        rep = {
            "name": rep_name,
            "ext": ext,
            "files": files,
            "frameStart": rep_frame_start,
            "frameEnd": rep_frame_end,
            # If expectedFile are absolute, we need only filenames
            "stagingDir": staging,
            "fps": instance_data.get("fps"),
            "tags": tags,
        }

        if instance_data.get("multipartExr", False):
            rep["tags"].append("multipartExr")

        # support conversion from tiled to scanline
        if instance_data.get("convertToScanline"):
            logger.info("Adding scanline conversion.")
            rep["tags"].append("toScanline")

        representations.append(rep)

        solve_families(instance_data, add_review)
    print(8)

    return representations
