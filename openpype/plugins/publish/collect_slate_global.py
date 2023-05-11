import os
import json
import pyblish.api
from openpype import resources


class CollectSlateGlobal(pyblish.api.InstancePlugin):
    """Inject the data needed to generate Slates in the enabled families."""
    label = "Collect for Slate Global workflow"
    order = pyblish.api.CollectorOrder + 0.499
    families = [
        "review",
        "render"
    ]

    def process(self, instance):

        context = instance.context
        slate_settings = context.data["project_settings"]["global"]\
            ["publish"].get("ExtractSlateGlobal")

        if not slate_settings:
            self.log.warning("No slate settings found. Skipping.")
            return

        if not slate_settings["enabled"]:
            self.log.warning("ExtractSlateGlobal is not active. Skipping.")
            return

        if context.data.get("host") == "nuke" and \
                "render.farm" in instance.data.get("families"):
            self.log.warning(
                "Skipping Slate Global Collect in Nuke context, defer to "
                "Deadline."
            )
            return

        self.log.info("ExtractSlateGlobal is active.")

        # Create dictionary of common data across all slates
        frame_padding = context.data["anatomy"]["templates"]["defaults"]\
            ["frame_padding"]
        slate_common_data = {
            "@version": str(instance.data["version"]).zfill(frame_padding),
            "frame_padding": frame_padding,
            "intent": {"label": "", "value": ""},
            "comment": "",
            "scope": "",
        }
        slate_common_data.update(instance.data["anatomyData"])
        if "customData" in instance.data:
            slate_common_data.update(instance.data["customData"])

        template_path = slate_settings["slate_template_path"].format(
            **os.environ
        )
        if not template_path:
            template_path = resources.get_resource(
                "slate_template", "generic_slate.html"
            )
            self.log.info(
                "No 'slate_template_path' found in project settings. "
                "Using default '%s'", template_path
            )

        resources_path = slate_settings["slate_resources_path"].format(
            **os.environ
        )
        if not resources_path:
            resources_path = resources.get_resource(
                "slate_template", "resources"
            )
            self.log.info(
                "No 'slate_resources_path' found in project settings. "
                "Using default '%s'", resources_path
            )

        slate_global = {
            "slate_template_path": template_path,
            "slate_resources_path": resources_path,
            "slate_profiles": slate_settings["profiles"],
            "slate_common_data": slate_common_data,
            "slate_thumbnail": "",
            "slate_repre_data": {},
            "slate_task_types": slate_settings["integrate_task_types"]
        }
        instance.data["slateGlobal"] = slate_global

        if "families" not in instance.data:
            instance.data["families"] = list()

        if "versionData" not in instance.data:
            instance.data["versionData"] = dict()

        if "families" not in instance.data["versionData"]:
            instance.data["versionData"]["families"] = list()

        task_type = instance.data["anatomyData"]["task"]["type"]
        if task_type in slate_settings["integrate_task_types"]:

            self.log.debug(
                "Task: %s is enabled for Extract Slate Global workflow, "
                "tagging for slate extraction on review families", task_type
            )

            instance.data["slate"] = True
            instance.data["families"].append("slate")
            instance.data["versionData"]["families"].append("slate")

            self.log.debug(
                "SlateGlobal Data: %s", json.dumps(
                    instance.data["slateGlobal"],
                    indent=4,
                    default=str
                )
            )
        else:
            self.log.debug(
                "Task: %s is disabled for Extract Slate Global workflow, "
                "skipping slate extraction on review families...", task_type
            )
