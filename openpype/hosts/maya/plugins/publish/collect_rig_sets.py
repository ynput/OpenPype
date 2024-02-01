import pyblish.api
from maya import cmds


class CollectRigSets(pyblish.api.InstancePlugin):
    """Ensure rig contains pipeline-critical content

    Every rig must contain at least two object sets:
        "controls_SET" - Set of all animatable controls
        "out_SET" - Set of all cacheable meshes

    """

    order = pyblish.api.CollectorOrder + 0.05
    label = "Collect Rig Sets"
    hosts = ["maya"]
    families = ["rig"]

    accepted_output = ["mesh", "transform"]
    accepted_controllers = ["transform"]

    def process(self, instance):

        # Find required sets by suffix
        searching = {"controls_SET", "out_SET",
                     "skeletonAnim_SET", "skeletonMesh_SET"}
        found = {}
        for node in cmds.ls(instance, exactType="objectSet"):
            for suffix in searching:
                if node.endswith(suffix):
                    found[suffix] = node
                    searching.remove(suffix)
                    break
            if not searching:
                break

        self.log.debug("Found sets: {}".format(found))
        rig_sets = instance.data.setdefault("rig_sets", {})
        for name, objset in found.items():
            rig_sets[name] = objset
