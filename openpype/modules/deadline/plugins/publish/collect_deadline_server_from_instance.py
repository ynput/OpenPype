# -*- coding: utf-8 -*-
"""Collect Deadline servers from instance.

This is resolving index of server lists stored in `deadlineServers` instance
attribute or using default server if that attribute doesn't exists.

"""
import pyblish.api
from openpype.pipeline.publish import KnownPublishError


class CollectDeadlineServerFromInstance(pyblish.api.InstancePlugin):
    """Collect Deadline Webservice URL from instance."""

    # Run before collect_render.
    order = pyblish.api.CollectorOrder + 0.005
    label = "Deadline Webservice from the Instance"
    families = ["rendering", "renderlayer"]
    hosts = ["maya"]

    def process(self, instance):
        instance.data["deadlineUrl"] = self._collect_deadline_url(instance)
        instance.data["deadlineUrl"] = \
            instance.data["deadlineUrl"].strip().rstrip("/")
        self.log.debug(
            "Using {} for submission.".format(instance.data["deadlineUrl"]))

    def _collect_deadline_url(self, render_instance):
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
        # Not all hosts can import this module.
        from maya import cmds
        deadline_settings = (
            render_instance.context.data
            ["system_settings"]
            ["modules"]
            ["deadline"]
        )

        default_server = render_instance.context.data["defaultDeadline"]
        instance_server = render_instance.data.get("deadlineServers")
        if not instance_server:
            self.log.debug("Using default server.")
            return default_server

        # Get instance server as sting.
        if isinstance(instance_server, int):
            instance_server = cmds.getAttr(
                "{}.deadlineServers".format(render_instance.data["objset"]),
                asString=True
            )

        default_servers = deadline_settings["deadline_urls"]
        project_servers = (
            render_instance.context.data
            ["project_settings"]
            ["deadline"]
            ["deadline_servers"]
        )
        if not project_servers:
            self.log.debug("Not project servers found. Using default servers.")
            return default_servers[instance_server]

        project_enabled_servers = {
            k: default_servers[k]
            for k in project_servers
            if k in default_servers
        }

        if instance_server not in project_enabled_servers:
            msg = (
                "\"{}\" server on instance is not enabled in project settings."
                " Enabled project servers:\n{}".format(
                    instance_server, project_enabled_servers
                )
            )
            raise KnownPublishError(msg)

        self.log.debug("Using project approved server.")
        return project_enabled_servers[instance_server]
