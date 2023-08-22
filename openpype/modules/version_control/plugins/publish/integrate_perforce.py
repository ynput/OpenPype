import os.path

import pyblish.api
import shutil

from openpype.modules.version_control.backends.perforce.api.rest_stub import (
    PerforceRestStub
)


class IntegratePerforce(pyblish.api.ContextPlugin):
    """Integrate perforce items
    """

    label = "Integrate Perforce items"
    order = pyblish.api.IntegratorOrder + 0.5

    def process(self, context):
        # PerforceRestStub.checkout("c:/projects/!perforce_workspace/text.txt")
        workfile_path = context.data["currentFile"]
        basename = os.path.basename(workfile_path)
        perforce_file_path = os.path.join("c:/Users/pypeclub/Perforce/perforce_workspace", basename)
        shutil.copy(workfile_path, perforce_file_path)
        result = PerforceRestStub.add(perforce_file_path, "Init commit")
        result = PerforceRestStub.submit_change_list("Init commit")
