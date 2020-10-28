import os
import pyblish.api
from pype.hosts.resolve.utils import get_resolve_module


class CollectProject(pyblish.api.ContextPlugin):
    """Collect Project object"""

    order = pyblish.api.CollectorOrder - 0.1
    label = "Collect Project"
    hosts = ["resolve"]

    def process(self, context):
        exported_projet_ext = ".drp"
        current_dir = os.getenv("AVALON_WORKDIR")
        resolve = get_resolve_module()
        PM = resolve.GetProjectManager()
        P = PM.GetCurrentProject()
        name = P.GetName()

        fname = name + exported_projet_ext
        current_file = os.path.join(current_dir, fname)
        normalised = os.path.normpath(current_file)

        context.data["project"] = P
        context.data["currentFile"] = normalised

        self.log.info(name)
        self.log.debug(normalised)
