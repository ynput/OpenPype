import os
from pprint import pformat
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
            "xml_preset_file": "Jpeg (8-bit).xml",
            "xml_preset_dir": "",
            "colorspace_out": "Output - sRGB",
            "representation_add_range": False,
            "representation_tags": ["thumbnail"]
        },
        "ftrackpreview": {
            "ext": "mov",
            "xml_preset_file": "Apple iPad (1920x1080).xml",
            "xml_preset_dir": "",
            "colorspace_out": "Output - Rec.709",
            "representation_add_range": True,
            "representation_tags": [
                "review",
                "delete"
            ]
        }
    }
    keep_original_representation = False

    # hide publisher during exporting
    hide_ui_on_process = True

    # settings
    export_presets_mapping = {}

    def process(self, instance):
        if (
            self.keep_original_representation
            and "representations" not in instance.data
            or not self.keep_original_representation
        ):
            instance.data["representations"] = []

        frame_start = instance.data["frameStart"]
        handle_start = instance.data["handleStart"]
        frame_start_handle = frame_start - handle_start
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
        # update them with settings and override in case the same
        # are found in there
        export_presets = deepcopy(self.default_presets)
        export_presets.update(self.export_presets_mapping)

        # with maintained duplication loop all presets
        with opfapi.maintained_object_duplication(clip) as duplclip:
            # loop all preset names and
            for unique_name, preset_config in export_presets.items():
                kwargs = {}
                preset_file = preset_config["xml_preset_file"]
                preset_dir = preset_config["xml_preset_dir"]
                repre_tags = preset_config["representation_tags"]
                color_out = preset_config["colorspace_out"]

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
                preset_path = str(os.path.join(
                    preset_dir, preset_file
                ))

                # define kwargs based on preset type
                if "thumbnail" in unique_name:
                    kwargs["thumb_frame_number"] = in_mark + (
                        source_duration_handles / 2)
                else:
                    kwargs.update({
                        "in_mark": in_mark,
                        "out_mark": out_mark
                    })

                export_dir_path = str(os.path.join(
                    staging_dir, unique_name
                ))
                os.makedirs(export_dir_path)

                # export
                opfapi.export_clip(
                    export_dir_path, duplclip, preset_path, **kwargs)

                extension = preset_config["ext"]
                # create representation data
                representation_data = {
                    "name": unique_name,
                    "outputName": unique_name,
                    "ext": extension,
                    "stagingDir": export_dir_path,
                    "tags": repre_tags,
                    "data": {
                        "colorspace": color_out
                    }
                }

                # collect all available content of export dir
                files = os.listdir(export_dir_path)

                # make sure no nested folders inside
                n_stage_dir, n_files = self._unfolds_nested_folders(
                    export_dir_path, files, extension)

                # fix representation in case of nested folders
                if n_stage_dir:
                    representation_data["stagingDir"] = n_stage_dir
                    files = n_files

                # add files to represetation but add
                # imagesequence as list
                if (
                    "movie_file" in preset_path
                    or unique_name == "thumbnail"
                ):
                    representation_data["files"] = files.pop()
                else:
                    representation_data["files"] = files

                # add frame range
                if preset_config["representation_add_range"]:
                    representation_data.update({
                        "frameStart": frame_start_handle,
                        "frameEnd": (
                            frame_start_handle + source_duration_handles),
                        "fps": instance.data["fps"]
                    })

                instance.data["representations"].append(representation_data)

                # add review family if found in tags
                if "review" in repre_tags:
                    instance.data["families"].append("review")

                self.log.info("Added representation: {}".format(
                    representation_data))

        self.log.debug("All representations: {}".format(
            pformat(instance.data["representations"])))

    def _unfolds_nested_folders(self, stage_dir, files_list, ext):
        """Unfolds nested folders

        Args:
            stage_dir (str): path string with directory
            files_list (list): list of file names
            ext (str): extension (jpg)[without dot]

        Raises:
            IOError: in case no files were collected form any directory

        Returns:
            str, list: new staging dir path, new list of file names
            or
            None, None: In case single file in `files_list`
        """
        # exclude single files which are having extension
        # the same as input ext attr
        if (
            # only one file in list
            len(files_list) == 1
            # file is having extension as input
            and ext in os.path.splitext(files_list[0])[-1]
        ):
            return None, None
        elif (
            # more then one file in list
            len(files_list) >= 1
            # extension is correct
            and ext in os.path.splitext(files_list[0])[-1]
            # test file exists
            and os.path.exists(
                os.path.join(stage_dir, files_list[0])
            )
        ):
            return None, None

        new_stage_dir = None
        new_files_list = []
        for file in files_list:
            search_path = os.path.join(stage_dir, file)
            if not os.path.isdir(search_path):
                continue
            for root, _dirs, files in os.walk(search_path):
                for _file in files:
                    _fn, _ext = os.path.splitext(_file)
                    if ext.lower() != _ext[1:].lower():
                        continue
                    new_files_list.append(_file)
                    if not new_stage_dir:
                        new_stage_dir = root

        if not new_stage_dir:
            raise AssertionError(
                "Files in `{}` are not correct! Check `{}`".format(
                    files_list, stage_dir)
            )

        return new_stage_dir, new_files_list
