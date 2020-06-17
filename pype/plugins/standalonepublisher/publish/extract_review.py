import os
import tempfile

import pyblish.api
import clique
import pype.api
import pype.lib


class ExtractReviewSP(pyblish.api.InstancePlugin):
    """Extracting Review mov file for Ftrack

    Compulsory attribute of representation is tags list with "review",
    otherwise the representation is ignored.

    All new represetnations are created and encoded by ffmpeg following
    presets found in `pype-config/presets/plugins/global/publish.json:ExtractReview:outputs`. To change the file extension
    filter values use preset's attributes `ext_filter`
    """

    label = "Extract Review SP"
    order = pyblish.api.ExtractorOrder + 0.02
    families = ["review"]
    hosts = ["standalonepublisher"]

    def process(self, instance):
        # adding plugin attributes from presets
        presets = instance.context.data["presets"]
        try:
            publish_presets = presets["plugins"]["standalonepublisher"]["publish"]
            plugin_attrs = publish_presets[self.__class__.__name__]
        except KeyError:
            raise KeyError("Preset for plugin \"{}\" are not set".format(
                self.__class__.__name__
            ))

        output_profiles = plugin_attrs.get("outputs", {})

        fps = instance.data.get("fps")
        start_frame = instance.data.get("frameStart")

        self.log.debug("Families In: `{}`".format(instance.data["families"]))

        # get specific profile if was defined
        specific_profiles = instance.data.get("repreProfiles", [])

        new_repres = []
        # filter out mov and img sequences
        for repre in instance.data["representations"]:
            tags = repre.get("tags", [])
            if "review" not in tags:
                continue

            staging_dir = repre["stagingDir"]
            for name in specific_profiles:
                profile = output_profiles.get(name)
                if not profile:
                    self.log.warning(
                        "Profile \"{}\" was not found in presets".format(name)
                    )
                    continue

                self.log.debug("Processing profile: {}".format(name))

                ext = profile.get("ext", None)
                if not ext:
                    ext = "mov"
                    self.log.debug((
                        "`ext` attribute not in output profile \"{}\"."
                        " Setting to default ext: `mov`"
                    ).format(name))

                if isinstance(repre["files"], list):
                    collections, remainder = clique.assemble(repre["files"])

                    full_input_path = os.path.join(
                        staging_dir,
                        collections[0].format("{head}{padding}{tail}")
                    )
                    filename = collections[0].format('{head}')
                    if filename.endswith("."):
                        filename = filename[:-1]
                else:
                    full_input_path = os.path.join(staging_dir, repre["files"])
                    filename = repre["files"].split(".")[0]

                # prepare output file
                repr_file = filename + "_{0}.{1}".format(name, ext)
                out_stagigng_dir = tempfile.mkdtemp(prefix="extract_review_")
                full_output_path = os.path.join(out_stagigng_dir, repr_file)

                self.log.info("input {}".format(full_input_path))
                self.log.info("output {}".format(full_output_path))

                repre_new = repre.copy()

                new_tags = [x for x in tags if x != "delete"]
                p_tags = profile.get("tags", [])
                self.log.info("p_tags: `{}`".format(p_tags))

                for _tag in p_tags:
                    if _tag not in new_tags:
                        new_tags.append(_tag)

                self.log.info("new_tags: `{}`".format(new_tags))

                input_args = []

                # overrides output file
                input_args.append("-y")

                # preset's input data
                input_args.extend(profile.get("input", []))

                # necessary input data
                # adds start arg only if image sequence
                if isinstance(repre["files"], list):
                    input_args.extend([
                        "-start_number {}".format(start_frame),
                        "-framerate {}".format(fps)
                    ])

                input_args.append("-i {}".format(full_input_path))

                output_args = []
                # preset's output data
                output_args.extend(profile.get("output", []))

                if isinstance(repre["files"], list):
                    # set length of video by len of inserted files
                    video_len = len(repre["files"])
                else:
                    video_len = repre["frameEnd"] - repre["frameStart"] + 1
                output_args.append(
                    "-frames {}".format(video_len)
                )

                # letter_box
                lb_string = (
                    "-filter:v "
                    "drawbox=0:0:iw:round((ih-(iw*(1/{0})))/2):t=fill:c=black,"
                    "drawbox=0:ih-round((ih-(iw*(1/{0})))/2):iw:"
                    "round((ih-(iw*(1/{0})))/2):t=fill:c=black"
                )
                letter_box = profile.get("letter_box", None)
                if letter_box:
                    output_args.append(lb_string.format(letter_box))

                # output filename
                output_args.append(full_output_path)

                ffmpeg_path = pype.lib.get_ffmpeg_tool_path("ffmpeg")
                mov_args = [
                    ffmpeg_path,
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
                    "name": name,
                    "ext": ext,
                    "files": repr_file,
                    "stagingDir": out_stagigng_dir,
                    "tags": new_tags,
                    "outputName": name,
                    "frameStartFtrack": 1,
                    "frameEndFtrack": video_len
                })
                # cleanup thumbnail from new repre
                if repre_new.get("thumbnail"):
                    repre_new.pop("thumbnail")
                if "thumbnail" in repre_new["tags"]:
                    repre_new["tags"].remove("thumbnail")

                # adding representation
                self.log.debug("Adding: {}".format(repre_new))
                # cleanup repre from preview
                if "preview" in repre:
                    repre.pop("preview")
                if "preview" in repre["tags"]:
                    repre["tags"].remove("preview")
                new_repres.append(repre_new)

        for repre in instance.data["representations"]:
            if "delete" in repre.get("tags", []):
                instance.data["representations"].remove(repre)

        for repre in new_repres:
            self.log.debug("Adding repre: \"{}\"".format(
                repre
            ))
            instance.data["representations"].append(repre)
