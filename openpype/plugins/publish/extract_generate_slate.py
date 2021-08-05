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
    order = pyblish.api.ExtractorOrder + 0.031
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
        representations = instance.data["representations"]

        self.log.debug("_ representations in: {}".format(
            representations
        ))

        self.new_representations = []
        self.to_clean_list = []

        # get context data
        anatomy_data = instance.data["anatomyData"]
        self.fps = anatomy_data.get("fps")

        # get ffmpeg path
        self.ffmpeg_path = openpype.lib.get_ffmpeg_tool_path("ffmpeg")

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

        # remove representations
        if not profile["keep_input"]:
            self.log.info(profile["keep_input"])
            self.remove_representation(instance, repre)

        # add new representations
        instance.data["representations"] += self.new_representations

        # removing temp files
        for f in self.to_clean_list:
            os.remove(f)
            self.log.debug("Removed: `{}`".format(f))

        self.log.debug("_ representations out: {}".format(
            pformat(instance.data["representations"])
        ))

        instance.data["families"].append("slate")

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
            new_repre = self.concut_slate_to_video(
                repre, slate_path, suffix, slate_width, slate_height)
            self.new_representations.append(new_repre)

            # add to later clearing
            self.to_clean_list.append(slate_path)

        # add to later clearing
        self.to_clean_list.append(thumbnail_path)

    def concut_slate_to_video(self, repre, slate_path, suffix, width, height):
        new_repre = copy.deepcopy(repre)
        video_input_path = self.get_input_path(repre)
        slate_v_path = self.get_output_path(repre, (suffix + "_slateVideo"))
        output_concut_path = self.get_output_path(repre, suffix)

        # add slate video frame to removal list
        self.to_clean_list.append(slate_v_path)

        # convert slate image to one frame video
        input_args = []
        output_args = []

        # preset's input data
        if repre.get("outputDef"):
            input_args.extend(repre["outputDef"].get('input', []))

        input_args.append("-loop 1 -i {}".format(slate_path))
        input_args.extend([
            "-r {}".format(repre.get("fps") or self.fps),
            "-vframes 1"]
        )

        # Codecs are copied from source for whole input
        codec_args = self.codec_args(repre)
        output_args.extend(codec_args)

        # make sure colors are correct
        output_args.extend([
            "-vf scale=out_color_matrix=bt709",
            "-color_primaries bt709",
            "-color_trc bt709",
            "-colorspace bt709"
        ])

        # overrides output file
        output_args.append("-y")
        output_args.append(slate_v_path)

        slate_args = [
            "\"{}\"".format(self.ffmpeg_path),
            " ".join(input_args),
            " ".join(output_args)
        ]
        slate_subprcs_cmd = " ".join(slate_args)

        # run slate generation subprocess
        self.log.debug("Slate Executing: {}".format(slate_subprcs_cmd))
        openpype.api.run_subprocess(
            slate_subprcs_cmd, shell=True, logger=self.log
        )

        # generate concut text file
        conc_text_path = self.get_output_path(
            repre, (suffix + "_concut"), "txt")

        self.to_clean_list.append(conc_text_path)
        self.log.debug("__ conc_text_path: {}".format(conc_text_path))

        new_line = "\n"
        with open(conc_text_path, "w") as conc_text_f:
            conc_text_f.writelines([
                "file {}".format(
                    slate_v_path.replace("\\", "/")),
                new_line,
                "file {}".format(video_input_path.replace("\\", "/"))
            ])

        # concat slate and videos together
        conc_input_args = [
            "-y",
            "-f concat",
            "-safe 0",
            "-i {}".format(conc_text_path)
        ]

        conc_output_args = [
            "-c copy",
            output_concut_path
        ]
        concat_args = [
            "\"{}\"".format(self.ffmpeg_path),
            " ".join(conc_input_args),
            " ".join(conc_output_args)
        ]
        concat_subprcs_cmd = " ".join(concat_args)

        # ffmpeg concat subprocess
        self.log.debug("Executing concat: {}".format(concat_subprcs_cmd))
        openpype.api.run_subprocess(
            concat_subprcs_cmd, shell=True, logger=self.log
        )
        new_name = repre["name"] + suffix
        frame_start = int(repre["frameStart"])

        new_repre.update({
            "name": new_name,
            "files": os.path.basename(output_concut_path),
            "stagingDir": os.path.dirname(output_concut_path),
            "outputName": new_name,
            "frameStart": frame_start - 1,
            "frameStartFtrack": frame_start - 1
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
            ext = _ext[1:]

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

        full_input_path = self.get_input_path(repre)
        full_output_path = self.get_output_path(repre, "_thumb", "jpg")

        self.log.info("output {}".format(full_output_path))

        jpeg_items = [
            "\"{}\"".format(self.ffmpeg_path),
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

    def remove_representation(self, instance, repre):
        file = repre["files"]
        dir = repre["stagingDir"]
        path = os.path.join(dir, file)
        self.log.warning("removing: {}".format(path))
        os.remove(path)
        instance.data["representations"].remove(repre)

    def codec_args(self, repre):
        """Detect possible codec arguments from representation."""
        codec_args = []

        # Get one filename of representation files
        filename = repre["files"]
        # If files is list then pick first filename in list
        if isinstance(filename, (tuple, list)):
            filename = filename[0]
        # Get full path to the file
        full_input_path = os.path.join(repre["stagingDir"], filename)

        try:
            # Get information about input file via ffprobe tool
            streams = openpype.lib.ffprobe_streams(full_input_path, self.log)
        except Exception:
            self.log.warning(
                "Could not get codec data from input.",
                exc_info=True
            )
            return codec_args

        # Try to find first stream that is not an audio
        no_audio_stream = None
        for stream in streams:
            if stream.get("codec_type") != "audio":
                no_audio_stream = stream
                break

        if no_audio_stream is None:
            self.log.warning((
                "Couldn't find stream that is not an audio from file \"{}\""
            ).format(full_input_path))
            return codec_args

        codec_name = no_audio_stream.get("codec_name")
        if codec_name:
            codec_args.append("-codec:v {}".format(codec_name))

        profile_name = no_audio_stream.get("profile")
        if profile_name:
            profile_name = profile_name.replace(" ", "_").lower()
            codec_args.append("-profile:v {}".format(profile_name))

        pix_fmt = no_audio_stream.get("pix_fmt")
        if pix_fmt:
            codec_args.append("-pix_fmt {}".format(pix_fmt))
        return codec_args

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
