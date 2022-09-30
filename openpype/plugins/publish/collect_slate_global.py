import os
import pyblish.api
from openpype.lib import (
    get_oiio_tools_path,
    get_ffmpeg_tool_path
)

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

        context = instance.context
        publ_settings = context.data["project_settings"]["global"]["publish"]
        version_padding = context.data["anatomy"]["templates"]["defaults"]["version_padding"]

        if self._slate_settings_name in publ_settings:

            settings = publ_settings[self._slate_settings_name]
            
            if not settings["enabled"]:
                self.log.warning("ExtractSlateGlobal is not active. Skipping...")
                return
            
            self.log.info("ExtractSlateGlobal is active.")

            tpl_path = settings["slate_template_path"].format(**os.environ)
            res_path = settings["slate_template_res_path"].format(**os.environ)
            _env = {
                "PATH": "{0};{1}".format(
                    os.path.dirname(get_oiio_tools_path()),
                    os.path.dirname(get_ffmpeg_tool_path())
                )
            }

            if not "slateGlobal" in instance.data:
                slate_global = instance.data["slateGlobal"] = {}

            slate_global.update({
                "slate_template_path": tpl_path,
                "slate_template_res_path": res_path,
                "slate_profiles": settings["profiles"],
                "slate_common_data": {},
                "slate_env": _env,
                "slate_thumbnail": "",
                "slate_repre_data": {}
            })
            
            slate_data = slate_global["slate_common_data"]
            slate_data.update(instance.data["anatomyData"])
            slate_data["@version"] = str(
                instance.data["version"]
            ).zfill(
                version_padding
            )
            slate_data["intent"] = {
                "label": "",
                "value": ""
            }
            slate_data["comment"] = ""
            slate_data["scope"] = ""

            if "customData" in instance.data:
                slate_data.update(instance.data["customData"])

            if not "versionData" in instance.data:
                versionData = {
                    "versionData": {
                        "families":[]
                    }
                }
                instance.data.update(versionData)
            instance.data["slate"] = True
            instance.data["families"].append("slate")
            instance.data["versionData"]["families"].append("slate")

            self.log.debug(
                "SlateGlobal Data: {}".format(slate_global)
            )