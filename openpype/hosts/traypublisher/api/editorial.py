
import os
import opentimelineio as otio
from openpype import lib as plib

from openpype.pipeline import (
    Creator,
    CreatedInstance
)

from .pipeline import (
    list_instances,
    update_instances,
    remove_instances,
    HostContext,
)



class CreateEditorialInstance:
    """Create Editorial OTIO timeline"""

    def __init__(self, file_path, extension=None, resources_dir=None):
        self.file_path = file_path
        self.video_extension = extension or ".mov"
        self.resources_dir = resources_dir

    def create(self):

        # get editorial sequence file into otio timeline object
        extension = os.path.splitext(self.file_path)[1]
        kwargs = {}
        if extension == ".edl":
            # EDL has no frame rate embedded so needs explicit
            # frame rate else 24 is asssumed.
            kwargs["rate"] = plib.get_asset()["data"]["fps"]

        instance.data["otio_timeline"] = otio.adapters.read_from_file(
            file_path, **kwargs)

        self.log.info(f"Added OTIO timeline from: `{file_path}`")
