import pyblish.api


class CollectAlembicCBAttrs(pyblish.api.InstancePlugin):
    """Collects settings for the Alembic extractor"""

    order = pyblish.api.CollectorOrder + 0.499
    families = ['colorbleed.model', 'colorbleed.pointcache']
    label = "Alembic Colorbleed Attrs"

    def process(self, instance):

        attrPrefix = instance.data.get("attrPrefix", [])
        attrPrefix.append("cb")
        instance.data['attrPrefix'] = attrPrefix

        # Ensure visibility keys are written
        instance.data['writeVisibility'] = True

        # Write creases
        instance.data['writeCreases'] = True

        # Ensure UVs are written
        instance.data['uvWrite'] = True

