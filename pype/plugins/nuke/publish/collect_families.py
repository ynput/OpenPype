import pyblish.api


@pyblish.api.log
class CollectInstanceFamilies(pyblish.api.ContextPlugin):
    """Collect families for all instances"""

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Families"
    hosts = ["nuke", "nukeassist"]

    def process(self, context):
        for instance in context.data["instances"]:

            if "write" in instance.data["family"]:
                node = instance[0]

                families = []
                if instance.data.get('families'):
                    families.append(instance.data['families'])

                # set for ftrack to accept
                # instance.data["families"] = ["ftrack"]

                if node["render"].value():
                    # dealing with local/farm rendering
                    if node["render_farm"].value():
                        families.append("render.farm")
                    else:
                        families.append("render.local")
                else:
                    families.append("render.frames")
                    # to ignore staging dir op in integrate
                    instance.data['transfer'] = False


                instance.data["families"] = families


        # Sort/grouped by family (preserving local index)
        context[:] = sorted(context, key=self.sort_by_family)

    def sort_by_family(self, instance):
        """Sort by family"""
        return instance.data.get("families", instance.data.get("family"))
