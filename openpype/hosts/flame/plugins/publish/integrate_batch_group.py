import os
from pprint import pformat
import pyblish
from openpype.lib import get_workdir
import openpype.hosts.flame.api as opfapi


@pyblish.api.log
class IntegrateBatchGroup(pyblish.api.InstancePlugin):
    """Integrate published shot to batch group"""

    order = pyblish.api.IntegratorOrder + 0.45
    label = "Integrate Batch Groups"
    hosts = ["flame"]
    families = ["clip"]

    def process(self, instance):
        frame_start = instance.data["frameStart"]
        frame_end = instance.data["frameEnd"]
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]
        asset_name = instance.data["asset"]
        add_tasks = instance.data["flameAddTasks"]

        # iterate all tasks from settings
        for task_data in add_tasks:
            # exclude batch group
            if not task_data["create_batch_group"]:
                continue
            task_name = task_data["name"]
            batchgroup_name = "{}_{}".format(asset_name, task_name)
            write_pref_data = self._get_write_prefs(instance, task_data)

            batch_data = {
                "shematic_reels": [
                    "OP_LoadedReel"
                ],
                "write_pref": write_pref_data,
                "handleStart": handle_start,
                "handleEnd": handle_end
            }
            self.log.debug(
                "__ batch_data: {}".format(pformat(batch_data)))

            # create batch with utils
            opfapi.create_batch(
                batchgroup_name,
                frame_start,
                frame_end,
                batch_data
            )

    def _get_write_prefs(self, instance, task_data):
        anatomy_data = instance.data["anatomyData"]

        task_workfile_path = self._get_shot_task_dir_path(instance, task_data)
        self.log.debug("__ task_workfile_path: {}".format(task_workfile_path))

        # TODO: this might be done with template in settings
        render_dir_path = os.path.join(
            task_workfile_path, "render", "flame")

        # TODO: add most of these to `imageio/flame/batch/write_node`
        name = "{project[code]}_{asset}_{task[name]}".format(
            **anatomy_data
        )

        # The path attribute where the rendered clip is exported
        # /path/to/file.[0001-0010].exr
        media_path = render_dir_path
        # name of file represented by tokens
        media_path_pattern = "<name>_v<iteration###>.<frame><ext>"
        # The Create Open Clip attribute of the Write File node. \
        # Determines if an Open Clip is created by the Write File node.
        create_clip = True
        # The Include Setup attribute of the Write File node.
        # Determines if a Batch Setup file is created by the Write File node.
        include_setup = True
        # The path attribute where the Open Clip file is exported by
        # the Write File node.
        create_clip_path = "<name>"
        # The path attribute where the Batch setup file
        # is exported by the Write File node.
        include_setup_path = "./<name>_v<iteration###>"
        # The file type for the files written by the Write File node.
        # Setting this attribute also overwrites format_extension,
        # bit_depth and compress_mode to match the defaults for
        # this file type.
        file_type = "OpenEXR"
        # The file extension for the files written by the Write File node.
        # This attribute resets to match file_type whenever file_type
        # is set. If you require a specific extension, you must
        # set format_extension after setting file_type.
        format_extension = "exr"
        # The bit depth for the files written by the Write File node.
        # This attribute resets to match file_type whenever file_type is set.
        bit_depth = "16"
        # The compressing attribute for the files exported by the Write
        # File node. Only relevant when file_type in 'OpenEXR', 'Sgi', 'Tiff'
        compress = True
        # The compression format attribute for the specific File Types
        # export by the Write File node. You must set compress_mode
        # after setting file_type.
        compress_mode = "DWAB"
        # The frame index mode attribute of the Write File node.
        # Value range: `Use Timecode` or `Use Start Frame`
        frame_index_mode = "Use Start Frame"
        frame_padding = 6
        # The versioning mode of the Open Clip exported by the Write File node.
        # Only available if create_clip = True.
        version_mode = "Follow Iteration"
        version_name = "v<version>"

        return {
            "name": name,
            "media_path": media_path,
            "media_path_pattern": media_path_pattern,
            "create_clip": create_clip,
            "include_setup": include_setup,
            "create_clip_path": create_clip_path,
            "include_setup_path": include_setup_path,
            "file_type": file_type,
            "format_extension": format_extension,
            "bit_depth": bit_depth,
            "compress": compress,
            "compress_mode": compress_mode,
            "frame_index_mode": frame_index_mode,
            "frame_padding": frame_padding,
            "version_mode": version_mode,
            "version_name": version_name
        }

    def _get_shot_task_dir_path(self, instance, task_data):
        project_doc = instance.data["projectEntity"]
        asset_entity = instance.data["assetEntity"]

        return get_workdir(
            project_doc, asset_entity, task_data["name"], "flame")
