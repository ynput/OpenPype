"""Create instances from batch data and continues in publish process.

Requires:
    CollectBatchData

Provides:
    context, instances -> All data from previous publishing process.
"""

import os
import clique
import tempfile
import math

from avalon import io
import pyblish.api
from openpype.lib import (
    prepare_template_data,
    get_asset,
    get_ffprobe_streams,
    convert_ffprobe_fps_value,
)
from openpype.lib.plugin_tools import (
    parse_json,
    get_subset_name_with_asset_doc
)


class CollectPublishedFiles(pyblish.api.ContextPlugin):
    """
    This collector will try to find json files in provided
    `OPENPYPE_PUBLISH_DATA`. Those files _MUST_ share same context.

    This covers 'basic' webpublishes, eg artists uses Standalone Publisher to
    publish rendered frames or assets.

    This is not applicable for 'studio' processing where host application is
    called to process uploaded workfile and render frames itself.
    """
    # must be really early, context values are only in json file
    order = pyblish.api.CollectorOrder - 0.490
    label = "Collect rendered frames"
    host = ["webpublisher"]
    targets = ["filespublish"]

    # from Settings
    task_type_to_family = []

    def process(self, context):
        batch_dir = context.data["batchDir"]
        task_subfolders = []
        for folder_name in os.listdir(batch_dir):
            full_path = os.path.join(batch_dir, folder_name)
            if os.path.isdir(full_path):
                task_subfolders.append(full_path)

        self.log.info("task_sub:: {}".format(task_subfolders))

        asset_name = context.data["asset"]
        asset_doc = get_asset()
        task_name = context.data["task"]
        task_type = context.data["taskType"]
        project_name = context.data["project_name"]
        for task_dir in task_subfolders:
            task_data = parse_json(os.path.join(task_dir,
                                                "manifest.json"))
            self.log.info("task_data:: {}".format(task_data))

            is_sequence = len(task_data["files"]) > 1

            _, extension = os.path.splitext(task_data["files"][0])
            family, families, tags = self._get_family(
                self.task_type_to_family,
                task_type,
                is_sequence,
                extension.replace(".", ''))

            subset_name = get_subset_name_with_asset_doc(
                family, task_data["variant"], task_name, asset_doc,
                project_name=project_name, host_name="webpublisher"
            )
            version = self._get_last_version(asset_name, subset_name) + 1

            instance = context.create_instance(subset_name)
            instance.data["asset"] = asset_name
            instance.data["subset"] = subset_name
            instance.data["family"] = family
            instance.data["families"] = families
            instance.data["version"] = version
            instance.data["stagingDir"] = tempfile.mkdtemp()
            instance.data["source"] = "webpublisher"

            # to convert from email provided into Ftrack username
            instance.data["user_email"] = task_data["user"]

            if is_sequence:
                instance.data["representations"] = self._process_sequence(
                    task_data["files"], task_dir, tags
                )
                instance.data["frameStart"] = \
                    instance.data["representations"][0]["frameStart"]
                instance.data["frameEnd"] = \
                    instance.data["representations"][0]["frameEnd"]
            else:
                frame_start = asset_doc["data"]["frameStart"]
                instance.data["frameStart"] = frame_start
                instance.data["frameEnd"] = asset_doc["data"]["frameEnd"]
                instance.data["representations"] = self._get_single_repre(
                    task_dir, task_data["files"], tags
                )
                file_url = os.path.join(task_dir, task_data["files"][0])
                no_of_frames = self._get_number_of_frames(file_url)
                if no_of_frames:
                    try:
                        frame_end = int(frame_start) + math.ceil(no_of_frames)
                        instance.data["frameEnd"] = math.ceil(frame_end) - 1
                        self.log.debug("frameEnd:: {}".format(
                            instance.data["frameEnd"]))
                    except ValueError:
                        self.log.warning("Unable to count frames "
                                         "duration {}".format(no_of_frames))

            # raise ValueError("STOP")
            instance.data["handleStart"] = asset_doc["data"]["handleStart"]
            instance.data["handleEnd"] = asset_doc["data"]["handleEnd"]

            self.log.info("instance.data:: {}".format(instance.data))

    def _get_subset_name(self, family, subset_template, task_name, variant):
        fill_pairs = {
            "variant": variant,
            "family": family,
            "task": task_name
        }
        subset = subset_template.format(**prepare_template_data(fill_pairs))
        return subset

    def _get_single_repre(self, task_dir, files, tags):
        _, ext = os.path.splitext(files[0])
        repre_data = {
            "name": ext[1:],
            "ext": ext[1:],
            "files": files[0],
            "stagingDir": task_dir,
            "tags": tags
        }
        self.log.info("single file repre_data.data:: {}".format(repre_data))
        return [repre_data]

    def _process_sequence(self, files, task_dir, tags):
        """Prepare representation for sequence of files."""
        collections, remainder = clique.assemble(files)
        assert len(collections) == 1, \
            "Too many collections in {}".format(files)

        frame_start = list(collections[0].indexes)[0]
        frame_end = list(collections[0].indexes)[-1]
        ext = collections[0].tail
        repre_data = {
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "name": ext[1:],
            "ext": ext[1:],
            "files": files,
            "stagingDir": task_dir,
            "tags": tags
        }
        self.log.info("sequences repre_data.data:: {}".format(repre_data))
        return [repre_data]

    def _get_family(self, settings, task_type, is_sequence, extension):
        """Guess family based on input data.

            Args:
                settings (dict): configuration per task_type
                task_type (str): Animation|Art etc
                is_sequence (bool): single file or sequence
                extension (str): without '.'

            Returns:
                (family, [families], tags) tuple
                AssertionError if not matching family found
        """
        task_type = task_type.lower()
        lower_cased_task_types = {}
        for t_type, task in settings.items():
            lower_cased_task_types[t_type.lower()] = task
        task_obj = lower_cased_task_types.get(task_type)
        assert task_obj, "No family configuration for '{}'".format(task_type)

        found_family = None
        families_config = []
        # backward compatibility, should be removed pretty soon
        if isinstance(task_obj, dict):
            for family, config in task_obj:
                config["result_family"] = family
                families_config.append(config)
        else:
            families_config = task_obj

        for config in families_config:
            if is_sequence != config["is_sequence"]:
                continue
            if (extension in config["extensions"] or
                    '' in config["extensions"]):  # all extensions setting
                found_family = config["result_family"]
                break

        msg = "No family found for combination of " +\
              "task_type: {}, is_sequence:{}, extension: {}".format(
                  task_type, is_sequence, extension)
        found_family = "render"
        assert found_family, msg

        return (found_family,
                config["families"],
                config["tags"])

    def _get_last_version(self, asset_name, subset_name):
        """Returns version number or 0 for 'asset' and 'subset'"""
        query = [
            {
                "$match": {"type": "asset", "name": asset_name}
            },
            {
                "$lookup":
                    {
                        "from": os.environ["AVALON_PROJECT"],
                        "localField": "_id",
                        "foreignField": "parent",
                        "as": "subsets"
                    }
            },
            {
                "$unwind": "$subsets"
            },
            {
                "$match": {"subsets.type": "subset",
                           "subsets.name": subset_name}},
            {
                "$lookup":
                    {
                        "from": os.environ["AVALON_PROJECT"],
                        "localField": "subsets._id",
                        "foreignField": "parent",
                        "as": "versions"
                    }
            },
            {
                "$unwind": "$versions"
            },
            {
                "$group": {
                    "_id": {
                        "asset_name": "$name",
                        "subset_name": "$subsets.name"
                    },
                    'version': {'$max': "$versions.name"}
                }
            }
        ]
        version = list(io.aggregate(query))

        if version:
            return version[0].get("version") or 0
        else:
            return 0

    def _get_number_of_frames(self, file_url):
        """Return duration in frames"""
        try:
            streams = get_ffprobe_streams(file_url, self.log)
        except Exception as exc:
            raise AssertionError((
                "FFprobe couldn't read information about input file: \"{}\"."
                " Error message: {}"
            ).format(file_url, str(exc)))

        first_video_stream = None
        for stream in streams:
            if "width" in stream and "height" in stream:
                first_video_stream = stream
                break

        if first_video_stream:
            nb_frames = stream.get("nb_frames")
            if nb_frames:
                try:
                    return int(nb_frames)
                except ValueError:
                    self.log.warning(
                        "nb_frames {} not convertible".format(nb_frames))

                    duration = stream.get("duration")
                    frame_rate = convert_ffprobe_fps_value(
                        stream.get("r_frame_rate", '0/0')
                    )
                    self.log.debug("duration:: {} frame_rate:: {}".format(
                        duration, frame_rate))
                    try:
                        return float(duration) * float(frame_rate)
                    except ValueError:
                        self.log.warning(
                            "{} or {} cannot be converted".format(duration,
                                                                  frame_rate))

        self.log.warning("Cannot get number of frames")
