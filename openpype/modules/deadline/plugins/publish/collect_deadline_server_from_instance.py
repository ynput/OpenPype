# -*- coding: utf-8 -*-
"""Collect Deadline servers from instance.

This is resolving index of server lists stored in `deadlineServers` instance
attribute or using default server if that attribute doesn't exists.

"""
import pyblish.api


class CollectDeadlineServerFromInstance(pyblish.api.InstancePlugin):
    """Collect Deadline Webservice URL from instance."""

    order = pyblish.api.CollectorOrder + 0.415
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

        default_server = render_instance.context.data["defaultDeadline"]
        instance_server = render_instance.data.get("deadlineServers")
        if not instance_server:
            return default_server

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
        # This is Maya specific and may not reflect real selection of deadline
        #   url as dictionary keys in Python 2 are not ordered
        return deadline_servers[
            list(deadline_servers.keys())[
                int(render_instance.data.get("deadlineServers"))
            ]
        ]
