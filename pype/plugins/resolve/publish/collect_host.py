import pyblish.api
from python_get_resolve import GetResolve


class CollectProject(pyblish.api.ContextPlugin):
    """Collect Project object"""

    order = pyblish.api.CollectorOrder - 0.1
    label = "Collect Project"
    hosts = ["resolve"]

    def process(self, context):
        resolve = GetResolve()
        PM = resolve.GetProjectManager()
        P = PM.GetCurrentProject()

        self.log.info(P.GetName())
