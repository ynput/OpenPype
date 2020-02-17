import os
import pyblish.api
import clique
import pype.api


class ExtractReview(pyblish.api.InstancePlugin):
    """Extracting Review mov file for Ftrack

    Compulsory attribute of representation is tags list with "review",
    otherwise the representation is ignored.

    All new represetnations are created and encoded by ffmpeg following
    presets found in `pype-config/presets/plugins/global/publish.json:ExtractReview:outputs`. To change the file extension
    filter values use preset's attributes `ext_filter`
    """

    label = "Extract Review"
    order = pyblish.api.ExtractorOrder + 0.02
    families = ["review"]
    hosts = ["nuke", "maya", "shell"]

    outputs = {}
    ext_filter = []

    def process(self, instance):
        to_width = 1920
        to_height = 1080

        output_profiles = self.outputs or {}

        inst_data = instance.data
        fps = inst_data.get("fps")
        start_frame = inst_data.get("frameStart")
        resolution_width = inst_data.get("resolutionWidth", to_width)
        resolution_height = inst_data.get("resolutionHeight", to_height)
        pixel_aspect = inst_data.get("pixelAspect", 1)
        self.log.debug("Families In: `{}`".format(inst_data["families"]))

        # get representation and loop them
        representations = inst_data["representations"]

        # filter out mov and img sequences
        representations_new = representations[:]
        for repre in representations:
            if repre['ext'] not in self.ext_filter:
                continue

            tags = repre.get("tags", [])

            if "thumbnail" in tags:
                continue

            self.log.info("Try repre: {}".format(repre))

            if "review" not in tags:
                continue

            staging_dir = repre["stagingDir"]

            # iterating preset output profiles
            for name, profile in output_profiles.items():
                repre_new = repre.copy()
                ext = profile.get("ext", None)
                p_tags = profile.get('tags', [])
                self.log.info("p_tags: `{}`".format(p_tags))

                # adding control for presets to be sequence
                # or single file
                is_sequence = ("sequence" in p_tags) and (ext in (
                    "png", "jpg", "jpeg"))

                self.log.debug("Profile name: {}".format(name))

                if not ext:
                    ext = "mov"
                    self.log.warning(
                        str("`ext` attribute not in output "
                            "profile. Setting to default ext: `mov`"))

                self.log.debug(
                    "instance.families: {}".format(
                        instance.data['families']))
                self.log.debug(
                    "profile.families: {}".format(profile['families']))

                profile_family_check = False
                for _family in profile['families']:
                    if _family in instance.data['families']:
                        profile_family_check = True
                        break

                if not profile_family_check:
                    continue

                if isinstance(repre["files"], list):
                    collections, remainder = clique.assemble(
                        repre["files"])

                    full_input_path = os.path.join(
                        staging_dir, collections[0].format(
                            '{head}{padding}{tail}')
                    )

                    filename = collections[0].format('{head}')
                    if filename.endswith('.'):
                        filename = filename[:-1]
                else:
                    full_input_path = os.path.join(
                        staging_dir, repre["files"])
                    filename = repre["files"].split(".")[0]

                repr_file = filename + "_{0}.{1}".format(name, ext)
                full_output_path = os.path.join(
                    staging_dir, repr_file)

                if is_sequence:
                    filename_base = filename + "_{0}".format(name)
                    repr_file = filename_base + ".%08d.{0}".format(
                        ext)
                    repre_new["sequence_file"] = repr_file
                    full_output_path = os.path.join(
                        staging_dir, filename_base, repr_file)

                self.log.info("input {}".format(full_input_path))
                self.log.info("output {}".format(full_output_path))

                new_tags = [x for x in tags if x != "delete"]

                # add families
                [instance.data["families"].append(t)
                    for t in p_tags
                    if t not in instance.data["families"]]

                # add to
                [new_tags.append(t) for t in p_tags
                 if t not in new_tags]

                self.log.info("new_tags: `{}`".format(new_tags))

                input_args = []

                # overrides output file
                input_args.append("-y")

                # preset's input data
                input_args.extend(profile.get('input', []))

                # necessary input data
                # adds start arg only if image sequence
                if isinstance(repre["files"], list):
                    input_args.append(
                        "-start_number {0} -framerate {1}".format(
                            start_frame, fps))

                input_args.append("-i {}".format(full_input_path))

                for audio in instance.data.get("audio", []):
                    offset_frames = (
                        instance.data.get("startFrameReview") -
                        audio["offset"]
                    )
                    offset_seconds = offset_frames / fps

                    if offset_seconds > 0:
                        input_args.append("-ss")
                    else:
                        input_args.append("-itsoffset")

                        input_args.append(str(abs(offset_seconds)))

                        input_args.extend(
                            ["-i", audio["filename"]]
                        )

                        # Need to merge audio if there are more
                        # than 1 input.
                        if len(instance.data["audio"]) > 1:
                            input_args.extend(
                                [
                                    "-filter_complex",
                                    "amerge",
                                    "-ac",
                                    "2"
                                ]
                            )

                output_args = []
                codec_args = profile.get('codec', [])
                output_args.extend(codec_args)
                # preset's output data
                output_args.extend(profile.get('output', []))

                # defining image ratios
                resolution_ratio = float(resolution_width / (
                    resolution_height * pixel_aspect))
                delivery_ratio = float(to_width) / float(to_height)
                self.log.debug(resolution_ratio)
                self.log.debug(delivery_ratio)

                # get scale factor
                scale_factor = to_height / (
                    resolution_height * pixel_aspect)
                self.log.debug(scale_factor)

                # letter_box
                lb = profile.get('letter_box', 0)
                if lb != 0:
                    ffmpet_width = to_width
                    ffmpet_height = to_height
                    if "reformat" not in p_tags:
                        lb /= pixel_aspect
                        if resolution_ratio != delivery_ratio:
                            ffmpet_width = resolution_width
                            ffmpet_height = int(
                                resolution_height * pixel_aspect)
                    else:
                        if resolution_ratio != delivery_ratio:
                            lb /= scale_factor
                        else:
                            lb /= pixel_aspect

                    output_args.append(str(
                        "-filter:v scale={0}x{1}:flags=lanczos,"
                        "setsar=1,drawbox=0:0:iw:"
                        "round((ih-(iw*(1/{2})))/2):t=fill:"
                        "c=black,drawbox=0:ih-round((ih-(iw*("
                        "1/{2})))/2):iw:round((ih-(iw*(1/{2})))"
                        "/2):t=fill:c=black").format(
                            ffmpet_width, ffmpet_height, lb))

                # In case audio is longer than video.
                output_args.append("-shortest")

                # output filename
                output_args.append(full_output_path)

                self.log.debug(
                    "__ pixel_aspect: `{}`".format(pixel_aspect))
                self.log.debug(
                    "__ resolution_width: `{}`".format(
                        resolution_width))
                self.log.debug(
                    "__ resolution_height: `{}`".format(
                        resolution_height))

                # scaling none square pixels and 1920 width
                if "reformat" in p_tags:
                    if resolution_ratio < delivery_ratio:
                        self.log.debug("lower then delivery")
                        width_scale = int(to_width * scale_factor)
                        width_half_pad = int((
                            to_width - width_scale)/2)
                        height_scale = to_height
                        height_half_pad = 0
                    else:
                        self.log.debug("heigher then delivery")
                        width_scale = to_width
                        width_half_pad = 0
                        scale_factor = float(to_width) / float(
                            resolution_width)
                        self.log.debug(scale_factor)
                        height_scale = int(
                            resolution_height * scale_factor)
                        height_half_pad = int(
                            (to_height - height_scale)/2)

                    self.log.debug(
                        "__ width_scale: `{}`".format(width_scale))
                    self.log.debug(
                        "__ width_half_pad: `{}`".format(
                            width_half_pad))
                    self.log.debug(
                        "__ height_scale: `{}`".format(
                            height_scale))
                    self.log.debug(
                        "__ height_half_pad: `{}`".format(
                            height_half_pad))

                    scaling_arg = str(
                        "scale={0}x{1}:flags=lanczos,"
                        "pad={2}:{3}:{4}:{5}:black,setsar=1"
                            ).format(width_scale, height_scale,
                                     to_width, to_height,
                                     width_half_pad,
                                     height_half_pad
                                     )

                    vf_back = self.add_video_filter_args(
                        output_args, scaling_arg)
                    # add it to output_args
                    output_args.insert(0, vf_back)

                # baking lut file application
                lut_path = instance.data.get("lutPath")
                if lut_path and ("bake-lut" in p_tags):
                    # removing Gama info as it is all baked in lut
                    gamma = next((g for g in input_args
                                  if "-gamma" in g), None)
                    if gamma:
                        input_args.remove(gamma)

                    # create lut argument
                    lut_arg = "lut3d=file='{}'".format(
                        lut_path.replace(
                            "\\", "/").replace(":/", "\\:/")
                            )
                    lut_arg += ",colormatrix=bt601:bt709"

                    vf_back = self.add_video_filter_args(
                        output_args, lut_arg)
                    # add it to output_args
                    output_args.insert(0, vf_back)
                    self.log.info("Added Lut to ffmpeg command")
                    self.log.debug(
                        "_ output_args: `{}`".format(output_args))

                if is_sequence:
                    stg_dir = os.path.dirname(full_output_path)

                    if not os.path.exists(stg_dir):
                        self.log.debug(
                            "creating dir: {}".format(stg_dir))
                        os.mkdir(stg_dir)

                mov_args = [
                    os.path.join(
                        os.environ.get(
                            "FFMPEG_PATH",
                            ""), "ffmpeg"),
                    " ".join(input_args),
                    " ".join(output_args)
                ]
                subprcs_cmd = " ".join(mov_args)

                # run subprocess
                self.log.debug("Executing: {}".format(subprcs_cmd))
                output = pype.api.subprocess(subprcs_cmd)
                self.log.debug("Output: {}".format(output))

                # create representation data
                repre_new.update({
                    'name': name,
                    'ext': ext,
                    'files': repr_file,
                    "tags": new_tags,
                    "outputName": name,
                    "codec": codec_args,
                    "_profile": profile,
                    "resolutionHeight": resolution_height,
                    "resolutionWidth": resolution_width,
                })
                if is_sequence:
                    repre_new.update({
                        "stagingDir": stg_dir,
                        "files": os.listdir(stg_dir)
                    })

                if repre_new.get('preview'):
                    repre_new.pop("preview")
                if repre_new.get('thumbnail'):
                    repre_new.pop("thumbnail")

                # adding representation
                self.log.debug("Adding: {}".format(repre_new))
                representations_new.append(repre_new)

        for repre in representations_new:
            if "delete" in repre.get("tags", []):
                representations_new.remove(repre)

        self.log.debug(
            "new representations: {}".format(representations_new))
        instance.data["representations"] = representations_new

        self.log.debug("Families Out: `{}`".format(instance.data["families"]))

    def add_video_filter_args(self, args, inserting_arg):
        """
        Fixing video filter argumets to be one long string

        Args:
            args (list): list of string arguments
            inserting_arg (str): string argument we want to add
                                 (without flag `-vf`)

        Returns:
            str: long joined argument to be added back to list of arguments

        """
        # find all video format settings
        vf_settings = [p for p in args
                       for v in ["-filter:v", "-vf"]
                       if v in p]
        self.log.debug("_ vf_settings: `{}`".format(vf_settings))

        # remove them from output args list
        for p in vf_settings:
            self.log.debug("_ remove p: `{}`".format(p))
            args.remove(p)
            self.log.debug("_ args: `{}`".format(args))

        # strip them from all flags
        vf_fixed = [p.replace("-vf ", "").replace("-filter:v ", "")
                    for p in vf_settings]

        self.log.debug("_ vf_fixed: `{}`".format(vf_fixed))
        vf_fixed.insert(0, inserting_arg)
        self.log.debug("_ vf_fixed: `{}`".format(vf_fixed))
        # create new video filter setting
        vf_back = "-vf " + ",".join(vf_fixed)

        return vf_back
