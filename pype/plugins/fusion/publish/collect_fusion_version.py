import pyblish.api


class CollectFusionVersion(pyblish.api.ContextPlugin):
    """Collect current comp"""

    order = pyblish.api.CollectorOrder
    label = "Collect Fusion Version"
    hosts = ["fusion"]

    def process(self, context):
        """Collect all image sequence tools"""

        comp = context.data.get("currentComp")
        if not comp:
            raise RuntimeError("No comp previously collected, unable to "
                               "retrieve Fusion version.")

        version = comp.GetApp().Version
        context.data["fusionVersion"] = version

        self.log.info("Fusion version: %s" % version)
