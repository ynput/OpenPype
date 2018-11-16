import pyblish.api

import avalon.fusion as fusion


class NukeRenderLocal(pyblish.api.InstancePlugin):
    # TODO: rewrite docstring to nuke
    """Render the current Fusion composition locally.

    Extract the result of savers by starting a comp render
    This will run the local render of Fusion.

    """

    order = pyblish.api.ExtractorOrder
    label = "Render Local"
    hosts = ["nuke"]
    families = ["write.local"]

    def process(self, instance):

        # This should be a ContextPlugin, but this is a workaround
        # for a bug in pyblish to run once for a family: issue #250
        context = instance.context
        key = "__hasRun{}".format(self.__class__.__name__)
        if context.data.get(key, False):
            return
        else:
            context.data[key] = True

        current_comp = context.data["currentFile"]
        start_frame = instance.data["startFrame"]
        end_frame = instance.data["end_frame"]

        self.log.info("Starting render")
        self.log.info("Start frame: {}".format(start_frame))
        self.log.info("End frame: {}".format(end_frame))

        # Render frames
        result = nuke.execute(
            node.name(),
            int(first_frame),
            int(last_frame)
        )

        if not result:
            raise RuntimeError("Comp render failed")
