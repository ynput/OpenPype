import pyblish.api
import avalon.api as avalon
import os

class CollectActiveProjectRoot(pyblish.api.ContextPlugin):
    """Inject the active project into context"""

    label = "Collect Project Root"
    order = pyblish.api.CollectorOrder - 0.1

    def process(self, context):
        S = avalon.Session
        context.data["projectroot"] = os.path.normpath(
            os.path.join(S['AVALON_PROJECTS'], S['AVALON_PROJECT'])
        )
