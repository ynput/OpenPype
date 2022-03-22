import pyblish
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
        write_pref_data = self._get_write_prefs(instance)

        batch_data = {
            "shematic_reels": [
                "OP_LoadedReel"
            ],
            "write_pref": write_pref_data,
            "handleStart": handle_start,
            "handleEnd": handle_end
        }

        opfapi.create_batch(asset_name, frame_start, frame_end, batch_data)

    def _get_write_prefs(self, instance):
        # The path attribute where the rendered clip is exported
        # /path/to/file.[0001-0010].exr
        media_path = "{render_path}".format()
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
        include_setup_path = None
        # The file type for the files written by the Write File node.
        # Setting this attribute also overwrites format_extension,
        # bit_depth and compress_mode to match the defaults for
        # this file type.
        file_type = "OpenEXR"
        # The bit depth for the files written by the Write File node.
        # This attribute resets to match file_type whenever file_type is set.
        bit_depth = "16"
        frame_index_mode = None
        frame_padding = 0
        # The versioning mode of the Open Clip exported by the Write File node.
        # Only available if create_clip = True.
        version_mode = "Follow Iteration"
        version_name = "v<version>"

        return {
            "media_path": media_path,
            "media_path_pattern": media_path_pattern,
            "create_clip": create_clip,
            "include_setup": include_setup,
            "create_clip_path": create_clip_path,
            "include_setup_path": include_setup_path,
            "file_type": file_type,
            "bit_depth": bit_depth,
            "frame_index_mode": frame_index_mode,
            "frame_padding": frame_padding,
            "version_mode": version_mode,
            "version_name": version_name
        }
