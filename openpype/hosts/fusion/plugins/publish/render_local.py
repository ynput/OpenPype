import os
from pprint import pformat

import pyblish.api
from openpype.hosts.fusion.api import comp_lock_and_undo_chunk


class Fusionlocal(pyblish.api.InstancePlugin):
    """Render the current Fusion composition locally.

    Extract the result of savers by starting a comp render
    This will run the local render of Fusion.

    """

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Render Local"
    hosts = ["fusion"]
    families = ["render.local"]

    def process(self, instance):

        context = instance.context
        key = "__hasRun{}".format(self.__class__.__name__)
        if context.data.get(key, False):
            return
        else:
            context.data[key] = True

        current_comp = context.data["currentComp"]
        frame_start = current_comp.GetAttrs("COMPN_RenderStart")
        frame_end = current_comp.GetAttrs("COMPN_RenderEnd")
        path = instance.data["path"]
        output_dir = instance.data["outputDir"]

        ext = os.path.splitext(os.path.basename(path))[-1]

        self.log.info("Starting render")
        self.log.info("Start frame: {}".format(frame_start))
        self.log.info("End frame: {}".format(frame_end))

        with comp_lock_and_undo_chunk(current_comp):
            result = current_comp.Render()

        if "representations" not in instance.data:
            instance.data["representations"] = []

        collected_frames = os.listdir(output_dir)
        repre = {
            'name': ext[1:],
            'ext': ext[1:],
            'frameStart': "%0{}d".format(len(str(frame_end))) % frame_start,
            'files': collected_frames,
            "stagingDir": output_dir,
        }
        instance.data["representations"].append(repre)

        # review representation
        repre_preview = repre.copy()
        repre_preview["name"] = repre_preview["ext"] = "mp4"
        repre_preview["tags"] = ["review", "preview", "ftrackreview", "delete"]
        instance.data["representations"].append(repre_preview)

        self.log.debug(f"_ instance.data: {pformat(instance.data)}")

        if not result:
            raise RuntimeError("Comp render failed")
