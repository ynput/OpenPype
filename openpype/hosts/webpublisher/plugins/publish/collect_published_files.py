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

import pyblish.api

from openpype.client import (
    get_asset_by_name,
    get_last_version_by_subset_name
)
from openpype.lib import (
    prepare_template_data,
    get_ffprobe_streams,
    convert_ffprobe_fps_value,
)
from openpype.pipeline.create import get_subset_name
from openpype_modules.webpublisher.lib import parse_json
from openpype.pipeline.version_start import get_versioning_start


class CollectPublishedFiles(pyblish.api.ContextPlugin):
    """
    This collector will try to find json files in provided
    `OPENPYPE_PUBLISH_DATA`. Those files _MUST_ share same context.

    This covers 'basic' webpublishes, eg artists uses Standalone Publisher to
    publish rendered frames or assets.

    This is not applicable for 'studio' processing where host application is
    called to process uploaded workfile and render frames itself.

    For each task configure what properties should resulting instance have
    based on uploaded files:
    - uploading sequence of 'png' >> create instance of 'render' family,
    by adding 'review' to 'Families' and 'Create review' to Tags it will
    produce review.

    There might be difference between single(>>image) and sequence(>>render)
    uploaded files.
    """
    # must be really early, context values are only in json file
    order = pyblish.api.CollectorOrder - 0.490
    label = "Collect rendered frames"
    hosts = ["webpublisher"]
    targets = ["filespublish"]

    # from Settings
    task_type_to_family = []
    sync_next_version = False  # find max version to be published, use for all

    def process(self, context):
        batch_dir = context.data["batchDir"]
        task_subfolders = []
        for folder_name in os.listdir(batch_dir):
            full_path = os.path.join(batch_dir, folder_name)
            if os.path.isdir(full_path):
                task_subfolders.append(full_path)

        self.log.info("task_sub:: {}".format(task_subfolders))

        project_name = context.data["project_name"]
        asset_name = context.data["asset"]
        asset_doc = get_asset_by_name(project_name, asset_name)
        task_name = context.data["task"]
        task_type = context.data["taskType"]
        project_name = context.data["project_name"]
        variant = context.data["variant"]

        next_versions = []
        instances = []
        for task_dir in task_subfolders:
            task_data = parse_json(os.path.join(task_dir,
                                                "manifest.json"))
            self.log.info("task_data:: {}".format(task_data))

            is_sequence = len(task_data["files"]) > 1
            first_file = task_data["files"][0]

            _, extension = os.path.splitext(first_file)
            extension = extension.lower()
            family, families, tags = self._get_family(
                self.task_type_to_family,
                task_type,
                is_sequence,
                extension.replace(".", ''))

            subset_name = get_subset_name(
                family,
                variant,
                task_name,
                asset_doc,
                project_name=project_name,
                host_name="webpublisher",
                project_settings=context.data["project_settings"]
            )
            version = self._get_next_version(
                project_name,
                asset_doc,
                task_name,
                task_type,
                family,
                subset_name,
                context
            )
            next_versions.append(version)

            instance = context.create_instance(subset_name)
            instance.data["asset"] = asset_name
            instance.data["subset"] = subset_name
            # set configurable result family
            instance.data["family"] = family
            # set configurable additional families
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
                if family != 'workfile':
                    file_url = os.path.join(task_dir, task_data["files"][0])
                    try:
                        no_of_frames = self._get_number_of_frames(file_url)
                        if no_of_frames:
                            frame_end = (
                                int(frame_start) + math.ceil(no_of_frames)
                            )
                            frame_end = math.ceil(frame_end) - 1
                            instance.data["frameEnd"] = frame_end
                            self.log.debug("frameEnd:: {}".format(
                                instance.data["frameEnd"]))
                    except Exception:
                        self.log.warning("Unable to count frames duration.")

            instance.data["handleStart"] = asset_doc["data"]["handleStart"]
            instance.data["handleEnd"] = asset_doc["data"]["handleEnd"]

            if "review" in tags:
                first_file_path = os.path.join(task_dir, first_file)
                instance.data["thumbnailSource"] = first_file_path

            instances.append(instance)
            self.log.info("instance.data:: {}".format(instance.data))

        if not self.sync_next_version:
            return

        # overwrite specific version with same version for all
        max_next_version = max(next_versions)
        for inst in instances:
            inst.data["version"] = max_next_version
            self.log.debug("overwritten version:: {}".format(max_next_version))

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
        ext = ext.lower()
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
        ext = ext.lower()
        repre_data = {
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "name": ext[1:],
            "ext": ext[1:],
            "files": files,
            "stagingDir": task_dir,
            "tags": tags  # configurable tags from Settings
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
            extensions = config.get("extensions") or []
            lower_extensions = set()
            for ext in extensions:
                if ext:
                    ext = ext.lower()
                    if ext.startswith("."):
                        ext = ext[1:]
                    lower_extensions.add(ext)

            # all extensions setting
            if not lower_extensions or extension in lower_extensions:
                found_family = config["result_family"]
                break

        msg = "No family found for combination of " +\
              "task_type: {}, is_sequence:{}, extension: {}".format(
                  task_type, is_sequence, extension)
        assert found_family, msg

        return (found_family,
                config["families"],
                config["tags"])

    def _get_next_version(
        self,
        project_name,
        asset_doc,
        task_name,
        task_type,
        family,
        subset_name,
        context
    ):
        """Returns version number or 1 for 'asset' and 'subset'"""

        version_doc = get_last_version_by_subset_name(
            project_name,
            subset_name,
            asset_doc["_id"],
            fields=["name"]
        )
        if version_doc:
            version = int(version_doc["name"]) + 1
        else:
            version = get_versioning_start(
                project_name,
                "webpublisher",
                task_name=task_name,
                task_type=task_type,
                family=family,
                subset=subset_name,
                project_settings=context.data["project_settings"]
            )

        return version

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
