import json
import tempfile

from openpype.lib import PreLaunchHook


class PreFtrackData(PreLaunchHook):
    """Pre-hook for openrv/ftrack
    """
    app_groups = ["openrv"]

    def execute(self):
        print("----- ---- ---- ---- ---")
        print("-------  OPENRV PreFtrackData ")
        print("----- ---- ---- ---- ---")


        representations = self.data.get("extra", None)
        if representations:
            payload = {"representations": representations}
            repr_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
            json.dump(payload, repr_file)
            repr_file.flush()

            self.launch_context.env["OPENPYPE_LOADER_REPRESENTATIONS"] = str(repr_file.name)
