import os
import pyblish.api
import subprocess
from pype.vendor import clique
from pypeapp import config


class ExtractReview(pyblish.api.InstancePlugin):
    """Resolve any dependency issies

    This plug-in resolves any paths which, if not updated might break
    the published file.

    The order of families is important, when working with lookdev you want to
    first publish the texture, update the texture paths in the nodes and then
    publish the shading network. Same goes for file dependent assets.
    """

    label = "Extract Review"
    order = pyblish.api.ExtractorOrder + 0.02
    families = ["review"]

    def process(self, instance):
        # adding plugin attributes from presets
        publish_presets = config.get_presets()["plugins"]["global"]["publish"]
        plugin_attrs = publish_presets[self.__class__.__name__]
        output_profiles = plugin_attrs.get("outputs", {})

        inst_data = instance.data
        fps = inst_data.get("fps")
        start_frame = inst_data.get("startFrame")

        # get representation and loop them
        representations = instance.data["representations"]

        # filter out mov and img sequences
        representations_new = list()
        for repre in representations:
            if repre['ext'] in plugin_attrs["ext_filter"]:
                tags = repre.get("tags", [])

                self.log.info("Try repre: {}".format(repre))

                if "review" in tags:

                    repre_new = repre.copy()
                    del(repre)

                    staging_dir = repre_new["stagingDir"]

                    if "mov" not in repre_new['ext']:
                        # get output presets and loop them
                        collected_frames = os.listdir(staging_dir)
                        collections, remainder = clique.assemble(
                            collected_frames)

                        full_input_path = os.path.join(
                            staging_dir, collections[0].format(
                                '{head}{padding}{tail}')
                        )

                        filename = collections[0].format('{head}')
                        if not filename.endswith('.'):
                            filename += "."
                        mov_file = filename + "mov"

                    else:
                        full_input_path = os.path.join(
                            staging_dir, repre_new["files"])

                        filename = repre_new["files"].split(".")[0]
                        mov_file = filename + ".mov"
                        # test if the file is not the input file
                        if not os.path.isfile(os.path.join(
                                staging_dir, mov_file)):
                            mov_file = filename + "_.mov"

                    full_output_path = os.path.join(staging_dir, mov_file)

                    self.log.info("input {}".format(full_input_path))
                    self.log.info("output {}".format(full_output_path))

                    for name, profile in output_profiles.items():
                        self.log.debug("Profile name: {}".format(name))
                        new_tags = tags + profile.get('tags', [])
                        input_args = []

                        # overrides output file
                        input_args.append("-y")

                        # preset's input data
                        input_args.extend(profile.get('input', []))

                        # necessary input data
                        # adds start arg only if image sequence
                        if "mov" not in repre_new['ext']:
                            input_args.append("-start_number {}".format(
                                start_frame))

                        input_args.append("-i {}".format(full_input_path))
                        input_args.append("-framerate {}".format(fps))

                        output_args = []
                        # preset's output data
                        output_args.extend(profile.get('output', []))

                        # output filename
                        output_args.append(full_output_path)
                        mov_args = [
                            "ffmpeg",
                            " ".join(input_args),
                            " ".join(output_args)
                        ]
                        subprocess_mov = " ".join(mov_args)

                        # run subprocess
                        sub_proc = subprocess.Popen(subprocess_mov)
                        sub_proc.wait()

                        if not os.path.isfile(full_output_path):
                            self.log.error(
                                "Quicktime wasn't created succesfully")

                        # create representation data
                        repre_new.update({
                            'name': name,
                            'ext': 'mov',
                            'files': mov_file,
                            "thumbnail": False,
                            "preview": True,
                            "tags": new_tags
                        })

                        # adding representation
                        representations_new.append(repre_new)
                else:
                    representations_new.append(repre)

        self.log.debug(
            "new representations: {}".format(representations_new))
        instance.data["representations"] = representations_new
