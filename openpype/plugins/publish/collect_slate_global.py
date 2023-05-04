import os
import json
import pyblish.api
from openpype.lib import (
    get_oiio_tools_path,
    get_ffmpeg_tool_path
)
from openpype import resources


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
        publish_settings = context.data["project_settings"]["global"]["publish"]
        version_padding = context.data["anatomy"]["templates"]["defaults"]\
            ["version_padding"]

        if self._slate_settings_name in publish_settings:

            settings = publish_settings[self._slate_settings_name]

            if not settings["enabled"]:
                self.log.warning("ExtractSlateGlobal is not active. Skipping...")
                return

            if instance.context.data.get("host") == "nuke" and \
                    "render.farm" in instance.data.get("families"):
                self.log.warning(
                    "Skipping Slate Global Collect in Nuke context, defer to Deadline."
                )
                return

            self.log.info("ExtractSlateGlobal is active.")
            # Create dictionary of common data across all Slates
            slate_common_data = {
                "@version":  str(instance.data["version"]).zfill(version_padding),
                "frame_padding": version_padding,
                "intent": {"label": "", "value": ""},
                "comment": "",
                "scope": "",
            }
            slate_common_data.update(instance.data["anatomyData"])
            if "customData" in instance.data:
                slate_common_data.update(instance.data["customData"])

            template_path = settings["slate_template_path"].format(**os.environ)
            if not template_path:
                template_path = resources.get_resource("slate_template", "generic_slate.html")
                self.log.info(
                    "No 'slate_template_path' found on the project settings. "
                    "Using default '%s'", template_path
                )
            resources_path = settings["slate_resources_path"].format(**os.environ)
            if not resources_path:
                resources_path = resources.get_resource("slate_template", "resources")
                self.log.info(
                    "No 'slate_resources_path' found on the project settings. "
                    "Using default '%s'", resources_path
                )
            slate_global = {
                "slate_template_path": template_path,
                "slate_resources_path": resources_path,
                "slate_profiles": settings["profiles"],
                "slate_common_data": slate_common_data,
                "slate_thumbnail": "",
                "slate_repre_data": {},
                "slate_task_types": settings["integrate_task_types"]
            }
            instance.data["slateGlobal"] = slate_global

            if "families" not in instance.data:
                instance.data["families"] = list()

            if "versionData" not in instance.data:
                instance.data["versionData"] = dict()

            if "families" not in instance.data["versionData"]:
                instance.data["versionData"]["families"] = list()

            if instance.data["anatomyData"]["task"]["type"] in \
                settings["integrate_task_types"]:

                self.log.debug("Task: {} is enabled for Extract Slate Global workflow, "
                    "tagging for slate extraction on review families...".format(
                        instance.data["anatomyData"]["task"]["type"]
                    )
                )

                instance.data["slate"] = True
                instance.data["families"].append("slate")
                instance.data["versionData"]["families"].append("slate")

                self.log.debug(
                    "SlateGlobal Data: {}".format(
                        json.dumps(
                            instance.data["slateGlobal"],
                            indent=4,
                            default=str
                        )
                    )
                )
            else:
                self.log.debug("Task: {} is disabled for Extract "
                    "Slate Global workflow, skipping slate "
                    "extraction on review families...".format(
                        instance.data["anatomyData"]["task"]["type"]
                ))
