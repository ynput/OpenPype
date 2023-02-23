import os
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
        
        # Start render
        self.render_once(context)

        frame_start = context.data["frameStartHandle"]
        frame_end = context.data["frameEndHandle"]
        path = instance.data["path"]
        output_dir = instance.data["outputDir"]

        basename = os.path.basename(path)
        head, ext = os.path.splitext(basename)
        files = [
            f"{head}{str(frame).zfill(4)}{ext}"
            for frame in range(frame_start, frame_end + 1)
        ]
        repre = {
            'name': ext[1:],
            'ext': ext[1:],
            'frameStart': f"%0{len(str(frame_end))}d" % frame_start,
            'files': files,
            "stagingDir": output_dir,
        }

        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(repre)

        # review representation
        repre_preview = repre.copy()
        repre_preview["name"] = repre_preview["ext"] = "mp4"
        repre_preview["tags"] = ["review", "ftrackreview", "delete"]
        instance.data["representations"].append(repre_preview)

    def render_once(self, context):
        """Render context comp only once, even with more render instances"""
        
        # This plug-in assumes all render nodes get rendered at the same time
        # to speed up the rendering. The check below makes sure that we only
        # execute the rendering once and not for each instance.
        key = f"__hasRun{self.__class__.__name__}"
        if context.data.get(key, False):
            return
        context.data[key] = True

        current_comp = context.data["currentComp"]
        frame_start = context.data["frameStartHandle"]
        frame_end = context.data["frameEndHandle"]

        self.log.info("Starting render")
        self.log.info(f"Start frame: {frame_start}")
        self.log.info(f"End frame: {frame_end}")

        with comp_lock_and_undo_chunk(current_comp):
            result = current_comp.Render({
                "Start": frame_start,
                "End": frame_end,
                "Wait": True
            })

        if not result:
            raise RuntimeError("Comp render failed")
