from avalon import api


class YetiCacheLoader(api.Loader):

    families = ["colorbleed.yeticache"]
    representations = ["fur"]

    label = "Load Yeti Cache"
    order = -9
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):


        pass
