# -*- coding: utf-8 -*-
"""Create ``Render`` instance in Maya."""
import os
import json
import appdirs
import requests
import six
import sys
from collections import Counter
import attr
import logging
from abc import ABCMeta

from maya import cmds  # noqa
import maya.app.renderSetup.model.renderSetup as renderSetup  # noqa

from openpype.hosts.maya.api import (
    lib,
    plugin
)
from openpype.api import (
    get_system_settings,
    get_project_settings,
    get_asset)
from openpype.modules import ModulesManager

from avalon.api import Session
from avalon.api import CreatorError


log = logging.getLogger(__name__)


class FarmFactory(object):
    pass


class CreateRender(plugin.Creator):
    """Create *render* instance."""

    label = "Render"
    family = "rendering"
    icon = "eye"
    defaults = ["Main"]

    _image_prefix_nodes = {
        'mentalray': 'defaultRenderGlobals.imageFilePrefix',
        'vray': 'vraySettings.fileNamePrefix',
        'arnold': 'defaultRenderGlobals.imageFilePrefix',
        'renderman': 'defaultRenderGlobals.imageFilePrefix',
        'redshift': 'defaultRenderGlobals.imageFilePrefix'
    }

    _image_prefixes = {
        'mentalray': 'maya/<Scene>/<RenderLayer>/<RenderLayer>{aov_separator}<RenderPass>',  # noqa
        'vray': 'maya/<scene>/<Layer>/<Layer>',
        'arnold': 'maya/<Scene>/<RenderLayer>/<RenderLayer>{aov_separator}<RenderPass>',  # noqa
        'renderman': 'maya/<Scene>/<layer>/<layer>{aov_separator}<aov>',
        'redshift': 'maya/<Scene>/<RenderLayer>/<RenderLayer>{aov_separator}<RenderPass>'  # noqa
    }

    _aov_chars = {
        "dot": ".",
        "dash": "-",
        "underscore": "_"
    }

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(CreateRender, self).__init__(*args, **kwargs)
        self.instance = None
        self.farm_instance = None
        self._project_settings = get_project_settings(
            Session["AVALON_PROJECT"])

        # process available render farm settings
        self.deadline_settings = get_system_settings()["modules"]["deadline"]
        self.muster_settings = get_system_settings()["modules"]["muster"]
        self.royalrender_settings = get_system_settings()["modules"]["royalrender"]

        if [deadline_settings["enabled"],
                muster_settings["enabled"],
                royalrender_settings["enabled"]].count(True) > 1:
            raise CreatorError("More then one render farm module enabled")

        try:
            self.aov_separator = self._aov_chars[(
                self._project_settings["maya"]
                ["create"]
                ["CreateRender"]
                ["aov_separator"]
            )]
        except KeyError:
            self.aov_separator = "_"

    def process(self):
        """Entry point."""
        if deadline_settings["enabled"]:
            self.farm_instance = DeadlineRenderInstance(
                Deadline, deadline_settings, self._project_settings)

        elif muster_settings["enabled"]:
            self.farm_module_settings = muster_settings

        elif royalrender_settings["enabled"]:
            self.farm_module_settings = royalrender_settings


        # check if render instance already exists
        exists = cmds.ls(self.name)
        if exists:
            cmds.warning("%s already exists." % exists[0])
            return

        with lib.undo_chunk():
            self.instance = super(CreateRender, self).process()
            self.data.update(
                self.farm_instance.module.get_instance_data(self.instance))
            self._create_render_settings()

    def _create_namespace(self):
        # create namespace with instance
        index = 1
        namespace_name = "_{}".format(str(self.instance))
        try:
            cmds.namespace(rm=namespace_name)
        except RuntimeError:
            # namespace is not empty, so we leave it untouched
            pass

        while cmds.namespace(exists=namespace_name):
            namespace_name = "_{}{}".format(str(self.instance), index)
            index += 1

        return cmds.namespace(add=namespace_name)

    def _create_render_settings(self):
        pass


@attr.s
class RenderInstance(object):
    module_klass = attr.ib()
    module_settings = attr.ib()
    project_settings = attr.ib()
    review = attr.ib(default=True)
    extendFrames = attr.ib(default=False)
    overrideExistingFrame = attr.ib(default=True)
    tileRendering = attr.ib(default=False)
    tilesX = attr.ib(default=2)
    tilesY = attr.ib(default=2)
    convertToScanline = attr.ib(default=False)
    useReferencedAovs = attr.ib(default=False)

    def __attrs_post_init__(self):
        # post initialization hook to instantiate class for farm
        # implementation
        self.module = self.module_klass(self)


@attr.s
class DeadlineRenderInstance(RenderInstance):
    deadlineServers = attr.ib(default=[])
    priority = attr.ib(default=50)
    framesPerTask = attr.ib(default=1)
    whitelist = attr.ib(default=False)
    machineList = attr.ib(default="")
    useMayaBatch = attr.ib(default=False)
    suspendPublishJob = attr.ib(default=False)


class FarmModule(object):
    def __init__(self, render_instance):
        # type: (RenderInstance) -> FarmModule
        self.settings = render_instance.module_settings
        self.project_settings = render_instance.project_settings
        self.render_instance = render_instance
        self.instance = None

    def get_instance_data(self):
        return {k: v for k, v in attr.asdict(self.render_instance)}


class Deadline(FarmModule):
    def __init__(self, render_instance):
        # type: (DeadlineRenderInstance) -> Deadline
        super(Deadline, self).__init__(render_instance)
        self.settings = render_instance.module_settings
        self.project_settings = render_instance.project_settings
        self.render_instance = render_instance
        self.instance = None
        self.deadline_servers = []
        self.server_aliases = []

        try:
            default_servers = self.settings["deadline_urls"]
            project_servers = (
                self.project_settings["deadline"]["deadline_servers"]
            )
            self.deadline_servers = {
                k: default_servers[k]
                for k in project_servers
                if k in default_servers
            }

            if not self.deadline_servers:
                self.deadline_servers = default_servers

        except AttributeError:
            # Handle situation were we had only one url for deadline.
            manager = ModulesManager()
            deadline_module = manager.modules_by_name["deadline"]
            # get default deadline webservice url from deadline module
            self.deadline_servers = deadline_module.deadline_urls

        # add Deadline server selection list
        if self.deadline_servers:
            cmds.scriptJob(
                attributeChange=[
                    "{}.deadlineServers".format(self.instance),
                    self._deadline_webservice_changed
                ])

    @staticmethod
    def get_deadline_pools(webservice):
        # type: (str) -> list
        """Get pools from Deadline.
        Args:
            webservice (str): Server url.
        Returns:
            list: Pools.
        Throws:
            CreatorError: If deadline webservice is unreachable.

        """
        argument = "{}/api/pools?NamesOnly=true".format(webservice)
        try:
            response = requests_get(argument)
        except requests.exceptions.ConnectionError as exc:
            msg = 'Cannot connect to deadline web service'
            log.error(msg)
            six.reraise(
                CreatorError,
                CreatorError('{} - {}'.format(msg, exc)),
                sys.exc_info()[2])
        else:
            if not response.ok:
                log.warning("No pools retrieved")
                return []

            return response.json()

    def _deadline_webservice_changed(self):
        """Refresh Deadline server dependent options."""
        # get selected server
        from maya import cmds  # noqa
        webservice = self.deadline_servers[
            self.server_aliases[
                cmds.getAttr("{}.deadlineServers".format(self.instance))
            ]
        ]
        pools = self.get_deadline_pools(webservice)
        cmds.deleteAttr("{}.primaryPool".format(self.instance))
        cmds.deleteAttr("{}.secondaryPool".format(self.instance))
        cmds.addAttr(self.instance, longName="primaryPool",
                     attributeType="enum",
                     enumName=":".join(pools))
        cmds.addAttr(self.instance, longName="secondaryPool",
                     attributeType="enum",
                     enumName=":".join(["-"] + pools))


def requests_post(*args, **kwargs):
    """Wrap request post method.

    Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
    variable is found. This is useful when Deadline or Muster server are
    running with self-signed certificates and their certificate is not
    added to trusted certificates on client machines.

    Warning:
        Disabling SSL certificate validation is defeating one line
        of defense SSL is providing and it is not recommended.

    """
    if "verify" not in kwargs:
        kwargs["verify"] = not os.getenv("OPENPYPE_DONT_VERIFY_SSL", True)
    return requests.post(*args, **kwargs)


def requests_get(*args, **kwargs):
    """Wrap request get method.

    Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
    variable is found. This is useful when Deadline or Muster server are
    running with self-signed certificates and their certificate is not
    added to trusted certificates on client machines.

    Warning:
        Disabling SSL certificate validation is defeating one line
        of defense SSL is providing and it is not recommended.

    """
    if "verify" not in kwargs:
        kwargs["verify"] = not os.getenv("OPENPYPE_DONT_VERIFY_SSL", True)
    return requests.get(*args, **kwargs)
