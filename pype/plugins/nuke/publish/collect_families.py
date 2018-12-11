import pyblish.api


@pyblish.api.log
class CollectInstanceFamilies(pyblish.api.ContextPlugin):
    """Collect families for all instances"""

    order = pyblish.api.CollectorOrder + 0.2
    label = "Define Families"
    hosts = ["nuke", "nukeassist"]

    def process(self, context):
        self.log.info('context.data["instances"]: {}'.format(context.data["instances"]))
        for instance in context.data["instances"]:

            if "write" in instance.data["family"]:
                if not instance.data["publish"]:
                    continue

                node = instance[0]

                if not node["render"].value():
                    families = [
                        "{}.frames".format(
                            instance.data["avalonKnob"]["families"]),
                        'ftrack']
                    # to ignore staging dir op in integrate
                    instance.data['transfer'] = False
                else:
                    # dealing with local/farm rendering
                    if node["render_farm"].value():
                        families = [
                            "{}.farm".format(
                                instance.data["avalonKnob"]["families"]),
                            'ftrack']
                    else:
                        families = [
                            "{}.local".format(
                                instance.data["avalonKnob"]["families"]),
                            'ftrack']

            instance.data.update({"families": families})

        # Sort/grouped by family (preserving local index)
        context[:] = sorted(context, key=self.sort_by_family)

    def sort_by_family(self, instance):
        """Sort by family"""
        return instance.data.get("families", instance.data.get("family"))
