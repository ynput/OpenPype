import os
import flame
from pprint import pformat
import openpype.hosts.flame.api as opfapi


class LoadClipBatch(opfapi.ClipLoader):
    """Load a subset to timeline as clip

    Place clip to timeline on its asset origin timings collected
    during conforming to project
    """

    families = ["render2d", "source", "plate", "render", "review"]
    representations = ["exr", "dpx", "jpg", "jpeg", "png", "h264"]

    label = "Load as clip to current batch"
    order = -10
    icon = "code-fork"
    color = "orange"

    # settings
    reel_name = "OP_LoadedReel"
    clip_name_template = "{asset}_{subset}_{output}"

    def load(self, context, name, namespace, options):

        # get flame objects
        self.batch = flame.batch

        # load clip to timeline and get main variables
        namespace = namespace
        version = context['version']
        version_data = version.get("data", {})
        version_name = version.get("name", None)
        colorspace = version_data.get("colorspace", None)

        # in case output is not in context replace key to representation
        if not context["representation"]["context"].get("output"):
            self.clip_name_template.replace("output", "representation")

        clip_name = self.clip_name_template.format(
            **context["representation"]["context"])

        # todo: settings in imageio
        # convert colorspace with ocio to flame mapping
        # in imageio flame section
        colorspace = colorspace

        # create workfile path
        workfile_dir = options.get("workdir") or os.environ["AVALON_WORKDIR"]
        openclip_dir = os.path.join(
            workfile_dir, clip_name
        )
        openclip_path = os.path.join(
            openclip_dir, clip_name + ".clip"
        )
        if not os.path.exists(openclip_dir):
            os.makedirs(openclip_dir)

        # prepare clip data from context ad send it to openClipLoader
        loading_context = {
            "path": self.fname.replace("\\", "/"),
            "colorspace": colorspace,
            "version": "v{:0>3}".format(version_name),
            "logger": self.log

        }
        self.log.debug(pformat(
            loading_context
        ))
        self.log.debug(openclip_path)

        # make openpype clip file
        opfapi.OpenClipSolver(openclip_path, loading_context).make()

        # prepare Reel group in actual desktop
        opc = self._get_clip(
            clip_name,
            openclip_path
        )

        # add additional metadata from the version to imprint Avalon knob
        add_keys = [
            "frameStart", "frameEnd", "source", "author",
            "fps", "handleStart", "handleEnd"
        ]

        # move all version data keys to tag data
        data_imprint = {
            key: version_data.get(key, str(None))
            for key in add_keys
        }
        # add variables related to version context
        data_imprint.update({
            "version": version_name,
            "colorspace": colorspace,
            "objectName": clip_name
        })

        # TODO: finish the containerisation
        # opc_segment = opfapi.get_clip_segment(opc)

        # return opfapi.containerise(
        #     opc_segment,
        #     name, namespace, context,
        #     self.__class__.__name__,
        #     data_imprint)

        return opc

    def _get_clip(self, name, clip_path):
        reel = self._get_reel()

        # with maintained openclip as opc
        matching_clip = None
        for cl in reel.clips:
            if cl.name.get_value() != name:
                continue
            matching_clip = cl

        if not matching_clip:
            created_clips = flame.import_clips(str(clip_path), reel)
            return created_clips.pop()

        return matching_clip

    def _get_reel(self):

        matching_reel = [
            rg for rg in self.batch.reels
            if rg.name.get_value() == self.reel_name
        ]

        return (
            matching_reel.pop()
            if matching_reel
            else self.batch.create_reel(str(self.reel_name))
        )
