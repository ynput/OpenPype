import pyblish.api


class CollectSetDress(pyblish.api.InstancePlugin):
    """Collect all relevant setdress items

    Collected data:

        * File name
        * Compatible loader
        * Matrix per instance
        * Namespace

    Note: GPU caches are currently not supported in the pipeline. There is no
    logic yet which supports the swapping of GPU cache to renderable objects.

    """

    order = pyblish.api.CollectorOrder + 0.49
    label = "Transformation of Items"
    families = ["colorbleed.setdress"]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found invalid transforms of setdress items")

    @classmethod
    def get_invalid(cls, instance):

        from colorbleed.maya import lib
        from maya import cmds

        invalid = []

        setdress_hierarchies = instance.data["hierarchy"]
        items = cmds.listRelatives(instance,
                                   allDescendents=True,
                                   type="transform",
                                   fullPath=True)
        for item in items:
            if item in setdress_hierarchies:
                continue



        return invalid
