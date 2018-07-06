import avalon.api


class AbcLoader(avalon.api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["colorbleed.animation", "colorbleed.pointcache"]
    label = "Reference animation"
    representations = ["abc"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):
        print("Not implemented")