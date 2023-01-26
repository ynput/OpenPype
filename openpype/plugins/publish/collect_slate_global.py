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
        version_padding = context.data["anatomy"]["templates"]["defaults"]\
            ["version_padding"]

        if self._slate_settings_name in publ_settings:

            settings = publ_settings[self._slate_settings_name]

            if not settings["enabled"]:
                self.log.warning("ExtractSlateGlobal is not active. Skipping...")
                return
            
            if instance.context.data.get("host") == "nuke" and (
                "render.farm" in instance.data.get("families")):
                self.log.warning("Skipping Slate Global Collect "
                    "in nuke context, defer to deadline...")
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

            if "slateGlobal" not in instance.data:
                slate_global = instance.data["slateGlobal"] = dict()

            slate_global.update({
                "slate_template_path": tpl_path,
                "slate_template_res_path": res_path,
                "slate_profiles": settings["profiles"],
                "slate_common_data": {},
                "slate_env": _env,
                "slate_thumbnail": "",
                "slate_repre_data": {},
                "slate_task_types": settings["integrate_task_types"]
            })

            slate_data = slate_global["slate_common_data"]
            slate_data.update(instance.data["anatomyData"])
            slate_data["@version"] = str(
                instance.data["version"]
            ).zfill(
                version_padding
            )
            slate_data["frame_padding"] = version_padding
            slate_data["intent"] = {
                "label": "",
                "value": ""
            }
            slate_data["comment"] = "-"
            slate_data["scope"] = "-"

            if "customData" in instance.data:
                slate_data.update(instance.data["customData"])

            if "families" not in instance.data:
                instance.data["families"] = list()

            if not "versionData" in instance.data:
                instance.data["versionData"] = dict()

            if "families" not in instance.data["versionData"]:
                instance.data["versionData"]["families"] = list()

            if instance.data["anatomyData"]["task"]["type"] in \
                settings["integrate_task_types"]:

                self.log.debug("Task: {} is enabled for Extract "
                    "Slate Global workflow, tagging for slate "
                    "extraction on review families...".format(
                        instance.data["anatomyData"]["task"]["type"]
                ))

                instance.data["slate"] = True
                instance.data["families"].append("slate")
                instance.data["versionData"]["families"].append("slate")

                self.log.debug(
                    "SlateGlobal Data: {}".format(
                        instance.data["slateGlobal"])
                )
            else:
                self.log.debug("Task: {} is disabled for Extract "
                    "Slate Global workflow, skipping slate "
                    "extraction on review families...".format(
                        instance.data["anatomyData"]["task"]["type"]
                ))