from pyblish import api


class CollectFramerate(api.ContextPlugin):
    """Collect framerate from selected sequence."""

    order = api.CollectorOrder + 0.001
    label = "Collect Framerate"
    hosts = ["hiero"]

    def process(self, context):
        sequence = context.data["activeSequence"]
        context.data["fps"] = self.get_rate(sequence)
        self.log.info("Framerate is collected: {}".format(context.data["fps"]))

    def get_rate(self, sequence):
        num, den = sequence.framerate().toRational()
        rate = float(num) / float(den)

        if rate.is_integer():
            return rate

        return round(rate, 3)
