import os

import pyblish.api
import pype.api
import pype.lib


class ExtractJpegEXR(pyblish.api.InstancePlugin):
    """Create jpg thumbnail from sequence using ffmpeg"""

    label = "Extract Jpeg EXR"
    hosts = ["shell"]
    order = pyblish.api.ExtractorOrder
    families = ["imagesequence", "render", "render2d", "source"]
    enabled = False

    def process(self, instance):

        self.log.info("subset {}".format(instance.data['subset']))
        if 'crypto' in instance.data['subset']:
            return

        # get representation and loop them
        representations = instance.data["representations"]

        # filter out mov and img sequences
        representations_new = representations[:]

        for repre in representations:
            tags = repre.get("tags", [])
            self.log.debug(repre)
            valid = 'review' in tags or "thumb-nuke" in tags
            if not valid:
                continue

            if not isinstance(repre['files'], list):
                continue

            if "multipartExr" in tags:
                # ffmpeg doesn't support multipart exrs
                continue

            stagingdir = os.path.normpath(repre.get("stagingDir"))
            input_file = repre['files'][0]

            # input_file = (
            #     collections[0].format('{head}{padding}{tail}') % start
            # )
            full_input_path = os.path.join(stagingdir, input_file)
            self.log.info("input {}".format(full_input_path))

            filename = os.path.splitext(input_file)[0]
            if not filename.endswith('.'):
                filename += "."
            jpeg_file = filename + "jpg"
            full_output_path = os.path.join(stagingdir, jpeg_file)

            self.log.info("output {}".format(full_output_path))

            config_data = instance.context.data['output_repre_config']

            proj_name = os.environ.get('AVALON_PROJECT', '__default__')
            profile = config_data.get(proj_name, config_data['__default__'])

            ffmpeg_path = pype.lib.get_ffmpeg_tool_path("ffmpeg")

            jpeg_items = []
            jpeg_items.append(ffmpeg_path)
            # override file if already exists
            jpeg_items.append("-y")
            # use same input args like with mov
            jpeg_items.extend(profile.get('input', []))
            # input file
            jpeg_items.append("-i {}".format(full_input_path))
            # output file
            jpeg_items.append(full_output_path)

            subprocess_jpeg = " ".join(jpeg_items)

            # run subprocess
            self.log.debug("{}".format(subprocess_jpeg))
            pype.api.subprocess(subprocess_jpeg)

            if "representations" not in instance.data:
                instance.data["representations"] = []

            representation = {
                'name': 'thumbnail',
                'ext': 'jpg',
                'files': jpeg_file,
                "stagingDir": stagingdir,
                "thumbnail": True,
                "tags": ['thumbnail']
            }

            # adding representation
            self.log.debug("Adding: {}".format(representation))
            representations_new.append(representation)

        instance.data["representations"] = representations_new
