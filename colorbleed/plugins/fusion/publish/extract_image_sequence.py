import pyblish.api


class ExtractImageSequence(pyblish.api.InstancePlugin):
    """Extract result of saver by starting a comp render

    This will run the local render of Fusion.

    """

    order = pyblish.api.ExtractorOrder
    label = "Render Local"
    hosts = ["fusion"]
    families = ["colorbleed.saver.renderlocal"]

    def process(self, instance):

        # This should be a ContextPlugin, but this is a workaround
        # for a bug in pyblish to run once for a family: issue #250
        context = instance.context
        key = "__hasRun{}".format(self.__class__.__name__)
        if context.data.get(key, False):
            return
        else:
            context.data[key] = True

        current_comp = context.data["currentComp"]
        start_frame = current_comp.GetAttrs("COMPN_RenderStart")
        end_frame = current_comp.GetAttrs("COMPN_RenderEnd")

        self.log.info("Starting render")
        self.log.info("Start frame: {}".format(start_frame))
        self.log.info("End frame: {}".format(end_frame))

        result = current_comp.Render()
        if not result:
            raise RuntimeError("Comp render failed")
