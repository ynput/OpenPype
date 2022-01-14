import os
from copy import deepcopy
import pyblish.api
import openpype.api
from openpype.hosts.flame import api as opfapi


class ExtractSubsetResources(openpype.api.Extractor):
    """
    Extractor for transcoding files from Flame clip
    """

    label = "Extract subset resources"
    order = pyblish.api.ExtractorOrder
    families = ["clip"]
    hosts = ["flame"]

    # plugin defaults
    default_presets = {
        "thumbnail": {
            "ext": "jpg",
            "xmlPresetFile": "Jpeg (8-bit).xml",
            "xmlPresetDir": "",
            "representationAddRange": False,
            "representationTags": ["thumbnail"]
        },
        "ftrackpreview": {
            "ext": "mov",
            "xmlPresetFile": "Apple iPad (1920x1080).xml",
            "xmlPresetDir": "",
            "representationAddRange": False,
            "representationTags": [
                "review",
                "delete"
            ]
        }
    }
    # hide publisher during exporting
    hide_ui_on_process = True

    # settings
    export_presets_mapping = {}

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

        # add default preset type for thumbnail and reviewable video
        # update them with settings and overide in case the same
        # are found in there
        export_presets = deepcopy(self.default_presets)
        export_presets.update(self.export_presets_mapping)

        # with maintained duplication loop all presets
        with opfapi.maintained_object_duplication(clip) as duplclip:
            # loop all preset names and
            for unique_name, preset_config in export_presets.items():
                kwargs = {}
                preset_file = preset_config["xmlPresetFile"]
                preset_dir = preset_config["xmlPresetDir"]

                # validate xml preset file is filled
                if preset_file == "":
                    raise ValueError(
                        ("Check Settings for {} preset: "
                         "`XML preset file` is not filled").format(
                            unique_name)
                    )

                # resolve xml preset dir if not filled
                if preset_dir == "":
                    preset_dir = opfapi.get_preset_path_by_xml_name(
                        preset_file)

                    if not preset_dir:
                        raise ValueError(
                            ("Check Settings for {} preset: "
                             "`XML preset file` {} is not found").format(
                                unique_name, preset_file)
                        )

                # create preset path
                preset_path = os.path.join(
                    preset_dir, preset_file
                )

                # define kwargs based on preset type
                if "thumbnail" in unique_name:
                    kwargs["thumb_frame_number"] = in_mark + (
                        source_duration_handles / 2)
                else:
                    kwargs.update({
                        "in_mark": in_mark,
                        "out_mark": out_mark
                    })

                export_dir_path = os.path.join(
                    staging_dir, unique_name
                )
                os.makedirs(export_dir_path)

                # export
                opfapi.export_clip(
                    export_dir_path, duplclip, preset_path, **kwargs)

                # create representation data
                representation_data = {
                    "name": unique_name,
                    "outputName": unique_name,
                    "ext": preset_config["ext"],
                    "stagingDir": export_dir_path,
                    "tags": preset_config["representationTags"]
                }

                files = os.listdir(export_dir_path)

                # add files to represetation but add
                # imagesequence as list
                if (
                    "movie_file" in preset_path
                    or unique_name == "thumbnail"
                ):
                    representation_data["files"] = files.pop()
                else:
                    representation_data["files"] = files

                instance.data["representations"].append(representation_data)

                self.log.info("Added representation: {}".format(
                    representation_data))
