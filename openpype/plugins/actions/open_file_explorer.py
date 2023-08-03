import os
import platform

from openpype.client import (
    get_asset_by_name,
)
from openpype.pipeline import (
    Anatomy,
    LauncherAction,
)
from openpype.pipeline.template_data import (
    get_asset_template_data,
)


class OpenTaskPath(LauncherAction):
    name = "open_task_path"
    label = "Open in File Browser"
    icon = None
    order = 500

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        return "AVALON_ASSET" in session

    def process(self, session, **kwargs):
        print(session)
        project_name = session["AVALON_PROJECT"]
        asset_name = session["AVALON_ASSET"]

        asset = get_asset_by_name(project_name, asset_name)

        anatomy = Anatomy(project_name)
        roots = anatomy.roots

        # We consider the first root to be the main one
        root_key = list(roots.keys())[0]
        root = roots.get(root_key)

        template_data = get_asset_template_data(asset, project_name)
        hierarchy = template_data.get("hierarchy")

        path = f"{root}/{project_name}/{hierarchy}/{asset_name}"

        platform_name = platform.system().lower()
        if platform_name == "windows":
            args = ["start", path]
        elif platform_name == "darwin":
            args = ["open", "-na", path]
        elif platform_name == "linux":
            args = ["xdg-open", path]
        else:
            raise Exception(f"Unknown platform {platform.system()}")
        # Make sure path is converted correctly for 'os.system'
        os.system(subprocess.list2cmdline(args))
