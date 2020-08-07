import pyblish.api
from pype.hosts.resolve.utils import get_resolve_module


class CollectProject(pyblish.api.ContextPlugin):
    """Collect Project object"""

    order = pyblish.api.CollectorOrder - 0.1
    label = "Collect Project"
    hosts = ["resolve"]

    def process(self, context):
        resolve = get_resolve_module()
        PM = resolve.GetProjectManager()
        P = PM.GetCurrentProject()

        self.log.info(P.GetName())
