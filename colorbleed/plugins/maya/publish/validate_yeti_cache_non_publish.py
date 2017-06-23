import pyblish.api
import colorbleed.api


class ValidateYetiCacheNonPublish(pyblish.api.InstancePlugin):
    """Validates Yeti caches are not published FROM published caches"""

    order = colorbleed.api.ValidateContentsOrder
    label = 'Yeti Cache Non Publish'
    families = ['colorbleed.furYeti']
    actions = [colorbleed.api.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):

        import cbra.lib

        invalid = list()
        for node, data in instance.data['yetiCaches'].items():

            source = data['source']

            # Published folder has at least "publish" in its path
            if "publish" not in source.lower():
                continue

            try:
                context = cbra.lib.parse_context(source)
            except RuntimeError:
                continue

            if "family" in context or "subset" in context:
                invalid.append(node)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            self.log.error("Invalid nodes: {0}".format(invalid))
            raise RuntimeError("Invalid yeti nodes in instance. "
                               "See logs for details.")
