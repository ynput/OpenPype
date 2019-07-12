import pyblish.api


@pyblish.api.log
class CollectRenderTarget(pyblish.api.InstancePlugin):
    """Collect families for all instances"""

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Render Target"
    hosts = ["nuke", "nukeassist"]
    families = ['write']

    def process(self, instance):

        node = instance[0]

        self.log.info('processing {}'.format(node))

        families = []
        if instance.data.get('families'):
            families += instance.data['families']

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

        families.append('ftrack')

        instance.data["families"] = families

        # Sort/grouped by family (preserving local index)
        instance.context[:] = sorted(instance.context, key=self.sort_by_family)

    def sort_by_family(self, instance):
        """Sort by family"""
        return instance.data.get("families", instance.data.get("family"))
