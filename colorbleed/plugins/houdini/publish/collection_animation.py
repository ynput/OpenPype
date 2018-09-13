import pyblish.api


class CollectAnimation(pyblish.api.InstancePlugin):
    """Collect the animation data for the data base

    Data collected:
        - start frame
        - end frame
        - nr of steps

    """

    label = "Collect Animation"
    families = ["colorbleed.pointcache"]

    def process(self, instance):

        node = instance[0]

        # Get animation parameters for data
        parameters = {"f1": "startFrame",
                      "f2": "endFrame",
                      "f3": "steps"}

        data = {}
        for par, translation in parameters.items():
            data[translation] = node.parm(par).eval()

        instance.data.update(data)
