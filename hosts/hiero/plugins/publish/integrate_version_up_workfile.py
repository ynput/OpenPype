from pyblish import api
import openpype.api as pype


class IntegrateVersionUpWorkfile(api.ContextPlugin):
    """Save as new workfile version"""

    order = api.IntegratorOrder + 10.1
    label = "Version-up Workfile"
    hosts = ["hiero"]

    optional = True
    active = True

    def process(self, context):
        project = context.data["activeProject"]
        path = context.data.get("currentFile")
        new_path = pype.version_up(path)

        if project:
            project.saveAs(new_path)

        self.log.info("Project workfile was versioned up")
