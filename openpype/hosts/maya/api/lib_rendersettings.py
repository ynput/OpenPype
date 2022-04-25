from maya import cmds

from openpype.api import (
    get_project_settings,
    get_asset)

from avalon.api import Session
from openpype.pipeline import CreatorError


class RenderSettzings(object):

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

    @classmethod
    def get_image_prefix_attr(cls, renderer):
        return cls._image_prefix_nodes[renderer]

    def __init__(self, project_settings):
        self._project_settings = project_settings

    @staticmethod
    def apply_defaults(renderer=None, project_settings=None):
        if renderer is None:
            renderer = cmds.getAttr(
                'defaultRenderGlobals.currentRenderer').lower()
            # handle various renderman names
            if renderer.startswith('renderman'):
                renderer = 'renderman'

        if project_settings is None:
            project_settings = get_project_settings(Session["AVALON_PROJECT"])

        render_settings = RenderSettings(project_settings)
        render_settings.set_default_renderer_settings(renderer)

    def set_default_renderer_settings(self, renderer):
        """Set basic settings based on renderer.

        Args:
            renderer (str): Renderer name.

        """
        # project_settings/maya/create/CreateRender/aov_separator
        try:
            aov_separator = self._aov_chars[(
                self._project_settings["maya"]
                                      ["create"]
                                      ["CreateRender"]
                                      ["aov_separator"]
            )]
        except KeyError:
            aov_separator = "_"

        prefix = self._image_prefixes[renderer]
        prefix = prefix.replace("{aov_separator}", aov_separator)
        cmds.setAttr(self._image_prefix_nodes[renderer],
                     prefix,
                     type="string")

        asset = get_asset()
        width = asset["data"].get("resolutionWidth")
        height = asset["data"].get("resolutionHeight")

        if renderer == "arnold":
            # set renderer settings for Arnold from project settings
            self._set_Arnold_settings(width, height)

        if renderer == "vray":
            self._set_vray_settings(aov_separator, width, height)

        if renderer == "redshift":
            self._set_redshift_settings(width, height)

    def _set_Arnold_settings(self, width, height):
        """Sets settings for Arnold."""

        img_ext = self.arnold_renderer.get("image_format")
        self._set_global_output_settings()
        cmds.setAttr("defaultArnoldDriver.ai_translator",
                    img_ext, type="string")
        cmds.setAttr("defaultResolution.width", width)
        cmds.setAttr("defaultResolution.height", height)

    def _set_redshift_settings(self, width, height):
        """Sets settings for Redshift."""

        img_ext = self.redshift_renderer.get("image_format")
        self._set_global_output_settings()
        cmds.setAttr("redshiftOptions.imageFormat", img_ext)
        cmds.setAttr("defaultResolution.width", width)
        cmds.setAttr("defaultResolution.height", height)

    def _set_vray_settings(self, aov_separator, width, height):
        # type: (str, int, int) -> None
        """Sets important settings for Vray."""
        settings = cmds.ls(type="VRaySettingsNode")
        node = settings[0] if settings else cmds.createNode("VRaySettingsNode")

        # Set aov separator
        # First we need to explicitly set the UI items in Render Settings
        # because that is also what V-Ray updates to when that Render Settings
        # UI did initialize before and refreshes again.
        MENU = "vrayRenderElementSeparator"
        if cmds.optionMenuGrp(MENU, query=True, exists=True):
            items = cmds.optionMenuGrp(MENU, query=True, ill=True)
            separators = [cmds.menuItem(i, query=True, label=True) for i in items]  # noqa: E501
            try:
                sep_idx = separators.index(aov_separator)
            except ValueError:
                raise CreatorError(
                    "AOV character {} not in {}".format(
                        aov_separator, separators))

            cmds.optionMenuGrp(MENU, edit=True, select=sep_idx + 1)

        # Set the render element attribute as string. This is also what V-Ray
        # sets whenever the `vrayRenderElementSeparator` menu items switch
        cmds.setAttr(
            "{}.fileNameRenderElementSeparator".format(node),
            aov_separator,
            type="string"
        )

        # Set render file format to exr
        cmds.setAttr("{}.imageFormatStr".format(node), "exr", type="string")

        # animType
        cmds.setAttr("{}.animType".format(node), 1)

        # resolution
        cmds.setAttr("{}.width".format(node), width)
        cmds.setAttr("{}.height".format(node), height)

    @staticmethod
    def _set_global_output_settings():
        # enable animation
        cmds.setAttr("defaultRenderGlobals.outFormatControl", 0)
        cmds.setAttr("defaultRenderGlobals.animation", 1)
        cmds.setAttr("defaultRenderGlobals.putFrameBeforeExt", 1)
        cmds.setAttr("defaultRenderGlobals.extensionPadding", 4)
