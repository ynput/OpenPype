import os

import pyblish.api
from pype.vendor import clique
import pype.api
from pypeapp import config


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

    def process(self, instance):
        # adding plugin attributes from presets
        publish_presets = config.get_presets()["plugins"]["global"]["publish"]
        plugin_attrs = publish_presets[self.__class__.__name__]
        output_profiles = plugin_attrs.get("outputs", {})

        inst_data = instance.data
        fps = inst_data.get("fps")
        start_frame = inst_data.get("frameStart")

        self.log.debug("Families In: `{}`".format(instance.data["families"]))

        # get representation and loop them
        representations = instance.data["representations"]

        # filter out mov and img sequences
        representations_new = representations[:]
        for repre in representations:
            if repre['ext'] in plugin_attrs["ext_filter"]:
                tags = repre.get("tags", [])

                self.log.info("Try repre: {}".format(repre))

                if "review" in tags:
                    staging_dir = repre["stagingDir"]
                    for name, profile in output_profiles.items():
                        self.log.debug("Profile name: {}".format(name))

                        ext = profile.get("ext", None)
                        if not ext:
                            ext = "mov"
                            self.log.warning(
                                "`ext` attribute not in output profile. Setting to default ext: `mov`")

                        self.log.debug("instance.families: {}".format(instance.data['families']))
                        self.log.debug("profile.families: {}".format(profile['families']))

                        if any(item in instance.data['families'] for item in profile['families']):
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

                            self.log.info("input {}".format(full_input_path))
                            self.log.info("output {}".format(full_output_path))

                            repre_new = repre.copy()

                            new_tags = [x for x in tags if x != "delete"]
                            p_tags = profile.get('tags', [])
                            self.log.info("p_tags: `{}`".format(p_tags))
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
                                input_args.append("-start_number {0} -framerate {1}".format(
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
                            # preset's output data
                            output_args.extend(profile.get('output', []))

                            # letter_box
                            # TODO: add to documentation
                            lb = profile.get('letter_box', None)
                            if lb:
                                output_args.append(
                                    "-filter:v drawbox=0:0:iw:round((ih-(iw*(1/{0})))/2):t=fill:c=black,drawbox=0:ih-round((ih-(iw*(1/{0})))/2):iw:round((ih-(iw*(1/{0})))/2):t=fill:c=black".format(lb))

                            # In case audio is longer than video.
                            output_args.append("-shortest")

                            # output filename
                            output_args.append(full_output_path)
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
                                "outputName": name
                            })
                            if repre_new.get('preview'):
                                repre_new.pop("preview")
                            if repre_new.get('thumbnail'):
                                repre_new.pop("thumbnail")

                            # adding representation
                            self.log.debug("Adding: {}".format(repre_new))
                            representations_new.append(repre_new)
                else:
                    continue
            else:
                continue

        for repre in representations_new:
            if "delete" in repre.get("tags", []):
                representations_new.remove(repre)

        self.log.debug(
            "new representations: {}".format(representations_new))
        instance.data["representations"] = representations_new

        self.log.debug("Families Out: `{}`".format(instance.data["families"]))
