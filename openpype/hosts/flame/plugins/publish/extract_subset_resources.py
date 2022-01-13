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
    hide_ui_on_process = True

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

        name = instance.data["name"]
        clip = instance.data["flameSourceClip"]
        staging_dir = self.staging_dir(instance)

        # prepare full export path
        export_dir_path = os.path.join(
            staging_dir, name
        )
        # loop all preset names and
        for preset_name, preset_config in self.export_presets_mapping:
            kwargs = {}
            unique_name = preset_config["uniqueName"]
            preset_type = None

            # define kwargs based on preset type
            if "thumbnail" in preset_name:
                kwargs["thumb_frame_number"] = 2
            else:
                preset_type = preset_config["preset_type"]
                kwargs.update({
                    "in_mark": 2,
                    "out_mark": 5,
                    "preset_type": preset_type
                })

            _export_dir_path = os.path.join(
                export_dir_path, unique_name
            )
            # export
            opfapi.export_clip(
                _export_dir_path, clip, preset_name, **kwargs)

            # create representation data
            representation_data = {
                'name': unique_name,
                'ext': preset_config["ext"],
                "stagingDir": _export_dir_path,
            }

            files = os.listdir(_export_dir_path)

            if preset_type and preset_type == "movie_file":
                representation_data["files"] = files
            else:
                representation_data["files"] = files.pop()

            instance.data["representations"].append(representation_data)

            self.log.info("Added representation: {}".format(
                representation_data))
