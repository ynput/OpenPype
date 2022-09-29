import os
import pyblish.api
from openpype.settings import get_current_project_settings
from openpype.settings.lib import get_anatomy_settings
from openpype.pipeline.context_tools import get_template_data_from_session



class CollectSlateGlobal(pyblish.api.InstancePlugin):
    """
    Check if slate global is active and enable slate workflow for
    selected families
    """
    label = "Collect for Slate Global workflow"
    order = pyblish.api.CollectorOrder + 0.499
    families = [
        "review",
        "render"
    ]

    _slate_settings_name = "ExtractSlateGlobal"

    def process(self, instance):

        publ_settings = get_current_project_settings()\
            ["global"]["publish"]
        version_padding = get_anatomy_settings(
            os.environ.get("AVALON_PROJECT")
        )["templates"]["defaults"]["version_padding"]

        if self._slate_settings_name in publ_settings:
            settings = publ_settings[self._slate_settings_name]
            self.log.debug(
                "__ Settings for ExtractSlateGlobal: {}".format(
                    settings
                )
            )
            if not settings["enabled"]:
                self.log.warning("ExtractSlateGlobal is not active. Skipping...")
                return
            
            self.log.info("ExtractSlateGlobal is active.")

            tpl_path = settings["slate_template_path"].format_map(os.environ)
            res_path = settings["slate_template_res_path"].format_map(os.environ)

            instance.data["slate"] = True
            instance.data["slateGlobal"] = {
                "slate_template_path": tpl_path,
                "slate_template_res_path": res_path,
                "slate_profiles": settings.get("profiles")
            }

            instance.data["version_padding"] = version_padding
            instance.data["families"].append("slate")
            
            # This is not clear. What is this supposed to be doing?
            if not "versionData" in instance.data:
                versionData = {
                    "versionData": {
                        "families":[]
                    }
                }
                instance.data.update(versionData)
            instance.data["versionData"]["families"].append("slate")
            
            if not "customData" in instance.data:
                instance.data["customData"] = {
                    "scope": ""
                }
            elif not "scope" in instance.data["customData"]:
                instance.data["customData"]["scope"] = ""
            
            self.log.debug(
                "__ instance.data: `{}`".format(instance.data)
            )