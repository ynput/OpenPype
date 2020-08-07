import pyblish.api
import nuke


class CollectReview(pyblish.api.InstancePlugin):
    """Collect review instance from rendered frames
    """

    order = pyblish.api.CollectorOrder + 0.3
    label = "Collect Review"
    hosts = ["nuke"]
    families = ["render", "render.local", "render.farm"]

    def process(self, instance):

        node = instance[0]

        if "review" not in node.knobs():
            knob = nuke.Boolean_Knob("review", "Review")
            knob.setValue(True)
            node.addKnob(knob)

        if not node["review"].value():
            return

        instance.data["families"].append("review")
        instance.data['families'].append('ftrack')

        self.log.info("Review collected: `{}`".format(instance))
        self.log.debug("__ instance.data: `{}`".format(instance.data))
