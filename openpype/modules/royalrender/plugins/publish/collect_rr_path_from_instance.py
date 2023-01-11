# -*- coding: utf-8 -*-
import pyblish.api


class CollectRRPathFromInstance(pyblish.api.InstancePlugin):
    """Collect RR Path from instance."""

    order = pyblish.api.CollectorOrder
    label = "Collect Royal Render path name from the Instance"
    families = ["rendering"]

    def process(self, instance):
        instance.data["rrPathName"] = self._collect_rr_path_name(instance)
        self.log.info(
            "Using '{}' for submission.".format(instance.data["rrPathName"]))

    @staticmethod
    def _collect_rr_path_name(render_instance):
        # type: (pyblish.api.Instance) -> str
        """Get Royal Render pat name from render instance."""
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

        return list(rr_servers.keys())[
                int(render_instance.data.get("rrPaths"))
            ]
