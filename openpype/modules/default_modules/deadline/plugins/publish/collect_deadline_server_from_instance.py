# -*- coding: utf-8 -*-
"""Collect Deadline servers from instance.

This is resolving index of server lists stored in `deadlineServers` instance
attribute or using default server if that attribute doesn't exists.

"""
import pyblish.api


class CollectDeadlineServerFromInstance(pyblish.api.InstancePlugin):
    """Collect Deadline Webservice URL from instance."""

    order = pyblish.api.CollectorOrder
    label = "Deadline Webservice from the Instance"
    families = ["rendering"]

    def process(self, instance):
        instance.data["deadlineUrl"] = self._collect_deadline_url(instance)
        self.log.info(
            "Using {} for submission.".format(instance.data["deadlineUrl"]))

    @staticmethod
    def _collect_deadline_url(render_instance):
        # type: (pyblish.api.Instance) -> str
        """Get Deadline Webservice URL from render instance.

        This will get all configured Deadline Webservice URLs and create
        subset of them based upon project configuration. It will then take
        `deadlineServers` from render instance that is now basically `int`
        index of that list.

        Args:
            render_instance (pyblish.api.Instance): Render instance created
                by Creator in Maya.

        Returns:
            str: Selected Deadline Webservice URL.

        """

        deadline_settings = (
            render_instance.context.data
            ["system_settings"]
            ["modules"]
            ["deadline"]
        )

        try:
            default_servers = deadline_settings["deadline_urls"]
            project_servers = (
                render_instance.context.data
                ["project_settings"]
                ["deadline"]
                ["deadline_servers"]
            )
            deadline_servers = {
                k: default_servers[k]
                for k in project_servers
                if k in default_servers
            }

        except AttributeError:
            # Handle situation were we had only one url for deadline.
            return render_instance.context.data["defaultDeadline"]

        return deadline_servers[
            list(deadline_servers.keys())[
                int(render_instance.data.get("deadlineServers"))
            ]
        ]
