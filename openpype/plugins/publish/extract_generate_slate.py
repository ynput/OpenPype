import os
import re
import copy
import json
import pyblish
import platform
from pprint import pformat

import openpype
from openpype.scripts import slates
from openpype.lib import filter_profiles


class ExtractGenerateSlate(openpype.api.Extractor):
    """ Extractor for dynamically generating slates.

    Slates are generated from previous representation file
    """

    label = "Extract generated slates"
    order = pyblish.api.ValidatorOrder - 0.1
    families = ["review"]
    hosts = [
        "nuke",
        "standalonepublisher"
    ]
    optional = True

    # Preset attributes
    profiles = None
    options = None

    def process(self, instance):
        # for dev
        instance.data["representations"] = representations = [{
            "name": "mp4",
            "ext": "mp4",
            "stagingDir": "C:/CODE/_PYPE_testing/testing_data/2d_shots/sh010/mov/cuts",
            "files": "mainsq02sh010_plate_sh010_h264burnin.mp4",
            "tags": ["generate-slate"]
        }]

        self.log.debug("_ representations in: {}".format(
            representations
        ))

        # get context data
        anatomy_data = instance.data["anatomyData"]

        # get filtering data
        host_name = anatomy_data["app"]
        family = self.main_family_from_instance(instance)
        families = instance.data["families"]

        filtering_criteria = {
            "hosts": host_name,
            "families": family
        }

        profile = filter_profiles(self.profiles, filtering_criteria)

        if not profile:
            self.log.info((
                "Skipped instance. None of profiles in presets are for "
                "Host: \"{}\" | Family: \"{}\" | "
            ).format(host_name, family))
            return

        for repre in representations:
            if "generate-slate" not in repre.get("tags"):
                continue

            # additional filtering
            slate_profiles = self.filter_inputs_by_families(profile, families)

            if not slate_profiles:
                self.log.info((
                    "Skipped instance. All slates definitions from selected"
                    " profile does not match to instance families. \"{}\""
                ).format(str(families)))
                return

            # generate slates
            self.generate_slates(repre, instance, slate_profiles)

        self.log.debug("_ representations out: {}".format(
            representations
        ))

    def generate_slates(self, repre, instance, slate_profiles):
        formating_data = {}
        # get context data
        context = instance.context
        anatomy_data = instance.data["anatomyData"]

        # generate paths
        thumbnail_path = self.generate_thumbnail(repre)

        # get options
        # fonts dir path
        fonts_dir = self.options.get("font_filepath", {}).get(
            platform.system().lower())
        fonts_dir = fonts_dir.format(**os.environ)
        # additional images path
        images_dir_path = self.options.get("images_path", {}).get(
            platform.system().lower())
        images_dir_path = images_dir_path.format(**os.environ)

        # prepare formating data for temmplate
        formating_data.update(anatomy_data)
        formating_data.update({
            "comment": context.data.get("comment", ""),
            "studio_name": context.data[
                "system_settings"]["general"]["studio_name"],
            "studio_code": context.data[
                "system_settings"]["general"]["studio_code"],
            "images_dir_path": images_dir_path,
            "thumbnail_path": thumbnail_path
        })
        self.log.debug(pformat(formating_data))
        # add environment variables for formating
        formating_data.update(os.environ)
        self.log.debug(pformat(formating_data))

        # get width and height from representation
        slate_width, slate_height = self.get_output_size(repre)

        remove_repre = []
        # iterate slate profiles and generate new
        for suffix, slate_def in slate_profiles.items():
            suffix = re.sub(
                '([a-zA-Z])', lambda x: x.groups()[0].upper(), suffix, 1)
            self.log.debug("suffix: {} | def: {}".format(
                suffix, pformat(slate_def)
            ))
            slate_path = self.get_output_path(repre, suffix, "png")
            # generate slate image
            slates.api.slate_generator(
                formating_data, json.loads(slate_def["template"]),
                output_path=slate_path,
                width=slate_width, height=slate_height, fonts_dir=fonts_dir
            )

            # Connecting generated slate image to input video
            new_repre = self.concut_slate_to_video(repre, slate_path, suffix)
            instance.data["representations"].append(new_repre)

            # remove intermediate files
            # os.remove(slate_path)

            remove_repre.append(slate_def["keep_input"])

        # remove temp files
        os.remove(thumbnail_path)

        # delete original representation only if allowed in settings
        if not any(remove_repre):
            instance.data["representations"].remove(repre)

    def concut_slate_to_video(self, repre, slate_path, suffix):
        new_repre = copy.deepcopy(repre)
        slate_v_path = self.get_output_path(repre, "_sv")
        output_concut_path = self.get_output_path(repre, suffix)

        # convert slate image to one frame video
        # generate concut text file
        # crate ffmpeg concut command
        # ffmpeg concut to new file

        new_repre.update({
            "name": repre["name"] + suffix,
            "files": os.path.basename(output_concut_path),
            "stagingDir": os.path.dirname(output_concut_path)
        })
        return new_repre

    def get_input_path(self, repre):
        stagingdir = os.path.normpath(repre['stagingDir'])
        input_file = repre['files']
        return os.path.join(stagingdir, input_file)

    def get_output_path(self, repre, suffix, ext=None):
        stagingdir = os.path.normpath(repre["stagingDir"])
        input_file = repre["files"]

        filename, _ext = os.path.splitext(input_file)
        # use original ext if ext input not defined
        if not ext:
            ext = _ext

        out_file_name = filename + suffix + "." + ext

        return os.path.join(stagingdir, out_file_name)

    def get_output_size(self, repre):
        full_input_path = self.get_input_path(repre)

        slate_streams = openpype.lib.ffprobe_streams(full_input_path, self.log)
        # Try to find first stream with defined 'width' and 'height'
        # - this is to avoid order of streams where audio can be as first
        # - there may be a better way (checking `codec_type`?)+
        width = None
        height = None
        for slate_stream in slate_streams:
            if "width" in slate_stream and "height" in slate_stream:
                width = int(slate_stream["width"])
                height = int(slate_stream["height"])
                break

        assert all([width, height]), AssertionError(
            "Missing Width and Height attributes in file: {}".format(
                full_input_path
            ))
        return (width, height)

    def generate_thumbnail(self, repre):
        ffmpeg_path = openpype.lib.get_ffmpeg_tool_path("ffmpeg")

        full_input_path = self.get_input_path(repre)
        full_output_path = self.get_output_path(repre, "_thumb", "jpg")

        self.log.info("output {}".format(full_output_path))

        jpeg_items = [
            "\"{}\"".format(ffmpeg_path),
            "-y",
            "-i {}".format(full_input_path),
            "-vframes 1",
            full_output_path,
        ]

        subprocess_jpeg = " ".join(jpeg_items)

        # run subprocess
        self.log.debug("{}".format(subprocess_jpeg))
        try:  # temporary until oiiotool is supported cross platform
            openpype.api.run_subprocess(
                subprocess_jpeg, shell=True, logger=self.log
            )
        except RuntimeError as exp:
            if "Compression" in str(exp):
                self.log.debug("Unsupported compression on input files. " +
                               "Skipping!!!")
                return
            raise

        return full_output_path

    def main_family_from_instance(self, instance):
        """Return main family of entered instance."""
        family = instance.data.get("family")
        if not family:
            family = instance.data["families"][0]
        return family

    @staticmethod
    def filter_inputs_by_families(profile, families):
        def _families_filter_validation(families, output_families_filter):
            """Determines if entered families intersect with families filters.

            All family values are lowered to avoid unexpected results.
            """
            if not output_families_filter:
                return True

            single_families = []
            combination_families = []
            for family_filter in output_families_filter:
                if not family_filter:
                    continue
                if isinstance(family_filter, (list, tuple)):
                    _family_filter = [
                        family.lower() for family in family_filter if family]
                    combination_families.append(_family_filter)
                else:
                    single_families.append(family_filter.lower())

            for family in single_families:
                if family in families:
                    return True

            for family_combination in combination_families:
                valid = all(
                    family in families for family in family_combination)
                if valid:
                    return True
            return False

        slates_profiles = profile.get("slates") or {}
        if not slates_profiles:
            return slates_profiles

        families = [family.lower() for family in families]

        filtered_slates = {}
        for filename_suffix, slate_def in slates_profiles.items():
            slate_filters = slate_def.get("filter")
            # If no filter on output preset, skip filtering and add output
            # profile for farther processing
            if not slate_filters:
                filtered_slates[filename_suffix] = slate_def
                continue

            families_filters = slate_filters.get("families")
            if not _families_filter_validation(families, families_filters):
                continue

            filtered_slates[filename_suffix] = slate_def

        return filtered_slates
