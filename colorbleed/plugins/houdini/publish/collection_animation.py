import pyblish.api


class CollectAnimation(pyblish.api.InstancePlugin):
    """Collect the animation data for the data base

    Data collected:
        - start frame
        - end frame
        - nr of steps

    """

    order = pyblish.api.CollectorOrder
    families = ["colorbleed.pointcache"]
    hosts = ["houdini"]
    label = "Collect Animation"

    def process(self, instance):

        node = instance[0]

        # Get animation parameters for data
        parameters = {"f1": "startFrame",
                      "f2": "endFrame",
                      "f3": "steps"}

        data = {name: node.parm(par).eval() for par, name in
                parameters.items()}

        instance.data.update(data)
