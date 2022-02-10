# -*- coding: utf-8 -*-
import pyblish.api


class CollectRRPathFromInstance(pyblish.api.InstancePlugin):
    """Collect RR Path from instance."""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Royal Render Path from the Instance"
    families = ["rendering"]

    def process(self, instance):
        instance.data["rrPath"] = self._collect_rr_path(instance)
        self.log.info(
            "Using {} for submission.".format(instance.data["rrPath"]))

    @staticmethod
    def _collect_rr_path(render_instance):
        # type: (pyblish.api.Instance) -> str
        """Get Royal Render path from render instance."""
        rr_settings = (
            render_instance.context.data
            ["system_settings"]
            ["modules"]
            ["royalrender"]
        )
        try:
            default_servers = rr_settings["rr_paths"]
            project_servers = (
                render_instance.context.data
                ["project_settings"]
                ["royalrender"]
                ["rr_paths"]
            )
            rr_servers = {
                k: default_servers[k]
                for k in project_servers
                if k in default_servers
            }

        except (AttributeError, KeyError):
            # Handle situation were we had only one url for royal render.
            return render_instance.context.data["defaultRRPath"]

        return rr_servers[
            list(rr_servers.keys())[
                int(render_instance.data.get("rrPaths"))
            ]
        ]
