# -*- coding: utf-8 -*-
from openpype.lib import PreLaunchHook
import os


class SetOperatorsPath(PreLaunchHook):
    """Set path to OpenPype assets folder."""

    app_groups = ["houdini"]

    def execute(self):
        hou_path = self.launch_context.env.get("HOUDINIPATH")

        openpype_assets = os.path.join(
            os.getenv("OPENPYPE_REPOS_ROOT"),
            "openpype", "hosts", "houdini", "hda"
        )

        if not hou_path:
            self.launch_context.env["HOUDINIPATH"] = openpype_assets
            return

        self.launch_context.env["HOUDINIPATH"] = "{}{}{}".format(
            hou_path, os.pathsep, openpype_assets
        )
