import pyblish.api


class CollectWriteLegacy(pyblish.api.InstancePlugin):
    """Collect legacy write nodes."""

    order = pyblish.api.CollectorOrder + 0.0101
    label = "Collect Write node Legacy"
    hosts = ["nuke", "nukeassist"]

    def process(self, instance):
        self.log.info(instance[:])
        node = instance[0]

        if node.Class() not in ["Group", "Write"]:
            return

        family_knobs = ["ak:family", "avalon:family"]
        test = [k for k in node.knobs().keys() if k in family_knobs]
        self.log.info(test)

        if len(test) == 1:
            if "render" in node[test[0]].value():
                self.log.info("render")
                return

        if "render" in node.knobs():
            instance.data.update(
                {"family": "write.legacy",
                 "families": []}
            )
