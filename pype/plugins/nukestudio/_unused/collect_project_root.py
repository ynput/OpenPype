import pyblish.api
import avalon.api as avalon
from pype.nukestudio.lib import set_multiroot_env
import os

class CollectActiveProjectRoot(pyblish.api.ContextPlugin):
    """Inject the active project into context"""

    label = "Collect Project Root"
    order = pyblish.api.CollectorOrder - 0.1

    def process(self, context):
        if not os.getenv("PYPE_ROOT_WORK"):
            set_multiroot_env()
        S = avalon.Session
        context.data["projectroot"] = os.path.normpath(
            os.path.join(os.getenv("PYPE_ROOT_WORK"), S['AVALON_PROJECT'])
        )
