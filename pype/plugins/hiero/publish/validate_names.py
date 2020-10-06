from pyblish import api


class ValidateNames(api.InstancePlugin):
    """Validate sequence, video track and track item names.

    When creating output directories with the name of an item, ending with a
    whitespace will fail the extraction.
    Exact matching to optimize processing.
    """

    order = api.ValidatorOrder
    families = ["clip"]
    match = api.Exact
    label = "Names"
    hosts = ["hiero"]

    def process(self, instance):

        item = instance.data["item"]

        msg = "Track item \"{0}\" ends with a whitespace."
        assert not item.name().endswith(" "), msg.format(item.name())

        msg = "Video track \"{0}\" ends with a whitespace."
        msg = msg.format(item.parent().name())
        assert not item.parent().name().endswith(" "), msg

        msg = "Sequence \"{0}\" ends with a whitespace."
        msg = msg.format(item.parent().parent().name())
        assert not item.parent().parent().name().endswith(" "), msg
