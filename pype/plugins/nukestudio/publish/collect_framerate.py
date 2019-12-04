from pyblish import api


class CollectFramerate(api.ContextPlugin):
    """Collect framerate from selected sequence."""

    order = api.CollectorOrder + 0.01
    label = "Collect Framerate"
    hosts = ["nukestudio"]

    def process(self, context):
        sequence = context.data["activeSequence"]
        context.data["fps"] = self.get_rate(sequence)

    def get_rate(self, sequence):
        num, den = sequence.framerate().toRational()
        rate = float(num) / float(den)

        if rate.is_integer():
            return rate

        return round(rate, 3)
