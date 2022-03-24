import os
import copy
from pprint import pformat
import pyblish
from openpype.lib import get_workdir
import openpype.hosts.flame.api as opfapi
import openpype.pipeline as op_pipeline


@pyblish.api.log
class IntegrateBatchGroup(pyblish.api.InstancePlugin):
    """Integrate published shot to batch group"""

    order = pyblish.api.IntegratorOrder + 0.45
    label = "Integrate Batch Groups"
    hosts = ["flame"]
    families = ["clip"]

    # settings
    default_loader = "LoadClip"

    def process(self, instance):
        add_tasks = instance.data["flameAddTasks"]

        # iterate all tasks from settings
        for task_data in add_tasks:
            # exclude batch group
            if not task_data["create_batch_group"]:
                continue

            # create or get already created batch group
            bgroup = self._get_batch_group(instance, task_data)

            # load plate to batch group
            self.log.info("Loading subset `{}` into batch `{}`".format(
                instance.data["subset"], bgroup.name.get_value()
            ))
            self._load_clip_to_context(instance, bgroup)

    def _load_clip_to_context(self, instance, bgroup):
        # get all loaders for host
        loaders = op_pipeline.discover_loader_plugins()

        # get all published representations
        published_representations = instance.data["published_representations"]

        # get all loadable representations
        representations = instance.data["representations"]

        # get repre_id for the loadable representations
        loadable_representations = [
            {
                "name": _repr["name"],
                "loader": _repr.get("batch_group_loader_name"),
                # match loader to the loadable representation
                "_id": next(
                    (
                        id
                        for id, repr in published_representations.items()
                        if repr["representation"]["name"] == _repr["name"]
                    ),
                    None
                )
            }
            for _repr in representations
            if _repr.get("load_to_batch_group") is not None
        ]

        # get representation context from the repre_id
        representation_ids = [
            repre["_id"]
            for repre in loadable_representations
            if repre["_id"] is not None
        ]
        repre_contexts = op_pipeline.load.get_repres_contexts(
            representation_ids)

        # loop all returned repres from repre_context dict
        for repre_id, repre_context in repre_contexts.items():
            # get loader name by representation id
            loader_name = next(
                (
                    repr["loader"]
                    for repr in loadable_representations
                    if repr["_id"] == repre_id
                ),
                self.default_loader
            )
            # get loader plugin
            Loader = next(
                (
                    loader_plugin
                    for loader_plugin in loaders
                    if loader_plugin.__name__ == loader_name
                ),
                None
            )
            if Loader:
                # load to flame by representation context
                try:
                    op_pipeline.load.load_with_repre_context(
                        Loader, repre_context)
                except op_pipeline.load.IncompatibleLoaderError as msg:
                    self.log.error(
                        "Check allowed representations for Loader `{}` "
                        "in settings > error: {}".format(
                            Loader.__name__, msg))
                    self.log.error(
                        "Representaton context >>{}<< is not compatible "
                        "with loader `{}`".format(
                            pformat(repre_context), Loader.__name__
                        )
                    )
            else:
                self.log.warning(
                    "Something got wrong and there is not Loader found for "
                    "following data: {}".format(
                        pformat(loadable_representations))
                )



    def _get_batch_group(self, instance, task_data):
        frame_start = instance.data["frameStart"]
        frame_end = instance.data["frameEnd"]
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]
        frame_duration = (frame_end - frame_start) + 1
        asset_name = instance.data["asset"]

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

        # check if the batch group already exists
        bgroup = opfapi.get_batch_group_from_desktop(batchgroup_name)

        if not bgroup:
            self.log.info(
                "Creating new batch group: {}".format(batchgroup_name))
            # create batch with utils
            bgroup = opfapi.create_batch(
                batchgroup_name,
                frame_start,
                frame_duration,
                **batch_data
            )
        else:
            self.log.info(
                "Updating batch group: {}".format(batchgroup_name))
            # update already created batch group
            bgroup.start_frame = frame_start
            bgroup.duration = frame_duration

        return bgroup

    def _get_anamoty_data_with_current_task(self, instance, task_data):
        anatomy_data = copy.deepcopy(instance.data["anatomyData"])
        task_name = task_data["name"]
        task_type = task_data["type"]
        anatomy_obj = instance.context.data["anatomy"]

        # update task data in anatomy data
        project_task_types = anatomy_obj["tasks"]
        task_code = project_task_types.get(task_type, {}).get("short_name")
        anatomy_data.update({
            "task": {
                "name": task_name,
                "type": task_type,
                "short": task_code
            }
        })
        return anatomy_data

    def _get_write_prefs(self, instance, task_data):
        # update task in anatomy data
        anatomy_data = self._get_anamoty_data_with_current_task(
            instance, task_data)

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
