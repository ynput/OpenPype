import os
import pyblish.api
import openpype.api
from openpype.hosts.flame import api as opfapi


class ExtractSubsetResources(openpype.api.Extractor):
    """
    Extractor for transcoding files from Flame clip
    """

    label = "Extract subset resources"
    order = pyblish.api.CollectorOrder + 0.49
    families = ["clip"]
    hosts = ["flame"]

    # hide publisher during exporting
    # hide_ui_on_process = True

    export_presets_mapping = {
        "thumbnail": {
            "ext": "jpg",
            "uniqueName": "thumbnail"
        },
        "OpenEXR (16-bit fp DWAA)_custom": {
            "ext": "exr",
            "preset_type": "file_sequence",
            "uniqueName": "exr16fpdwaa"
        },
        "QuickTime (H.264 1080p 8Mbits)_custom": {
            "ext": "mov",
            "preset_type": "movie_file",
            "uniqueName": "ftrackpreview"
        }
    }

    def process(self, instance):
        # create representation data
        if "representations" not in instance.data:
            instance.data["representations"] = []

        source_first_frame = instance.data["sourceFirstFrame"]
        source_start_handles = instance.data["sourceStartH"]
        source_end_handles = instance.data["sourceEndH"]
        source_duration_handles = (
            source_end_handles - source_start_handles) + 1

        clip_data = instance.data["flameSourceClip"]
        clip = clip_data["PyClip"]

        in_mark = (source_start_handles - source_first_frame) + 1
        out_mark = in_mark + source_duration_handles

        staging_dir = self.staging_dir(instance)

        # loop all preset names and
        for preset_name, preset_config in self.export_presets_mapping.items():
            kwargs = {}
            unique_name = preset_config["uniqueName"]
            preset_type = None

            # define kwargs based on preset type
            if "thumbnail" in preset_name:
                kwargs["thumb_frame_number"] = in_mark + (
                    source_duration_handles / 2)
            else:
                preset_type = preset_config["preset_type"]
                kwargs.update({
                    "in_mark": in_mark,
                    "out_mark": out_mark,
                    "export_type": preset_type
                })

            export_dir_path = os.path.join(
                staging_dir, unique_name
            )
            os.makedirs(export_dir_path)

            # export
            opfapi.export_clip(
                export_dir_path, clip, preset_name, **kwargs)

            # create representation data
            representation_data = {
                'name': unique_name,
                'ext': preset_config["ext"],
                "stagingDir": export_dir_path,
            }

            files = os.listdir(export_dir_path)

            # add files to represetation but add
            # imagesequence as list
            if (
                preset_type
                and preset_type == "movie_file"
                or preset_name == "thumbnail"
            ):
                representation_data["files"] = files.pop()
            else:
                representation_data["files"] = files

            instance.data["representations"].append(representation_data)

            self.log.info("Added representation: {}".format(
                representation_data))
