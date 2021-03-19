# -*- coding: utf-8 -*-
"""Module handling expected render output from Maya.

This module is used in :mod:`collect_render` and :mod:`collect_vray_scene`.

Note:
    To implement new renderer, just create new class inheriting from
    :class:`AExpectedFiles` and add it to :func:`ExpectedFiles.get()`.

Attributes:
    R_SINGLE_FRAME (:class:`re.Pattern`): Find single frame number.
    R_FRAME_RANGE (:class:`re.Pattern`): Find frame range.
    R_FRAME_NUMBER (:class:`re.Pattern`): Find frame number in string.
    R_LAYER_TOKEN (:class:`re.Pattern`): Find layer token in image prefixes.
    R_AOV_TOKEN (:class:`re.Pattern`): Find AOV token in image prefixes.
    R_SUBSTITUTE_AOV_TOKEN (:class:`re.Pattern`): Find and substitute AOV token
        in image prefixes.
    R_REMOVE_AOV_TOKEN (:class:`re.Pattern`): Find and remove AOV token in
        image prefixes.
    R_CLEAN_FRAME_TOKEN (:class:`re.Pattern`): Find and remove unfilled
        Renderman frame token in image prefix.
    R_CLEAN_EXT_TOKEN (:class:`re.Pattern`): Find and remove unfilled Renderman
        extension token in image prefix.
    R_SUBSTITUTE_LAYER_TOKEN (:class:`re.Pattern`): Find and substitute render
        layer token in image prefixes.
    R_SUBSTITUTE_SCENE_TOKEN (:class:`re.Pattern`): Find and substitute scene
        token in image prefixes.
    R_SUBSTITUTE_CAMERA_TOKEN (:class:`re.Pattern`): Find and substitute camera
        token in image prefixes.
    RENDERER_NAMES (dict): Renderer names mapping between reported name and
        *human readable* name.
    IMAGE_PREFIXES (dict): Mapping between renderers and their respective
        image prefix attribute names.

Todo:
    Determine `multipart` from render instance.

"""

import types
import re
import os
from abc import ABCMeta, abstractmethod

import six

import pype.hosts.maya.api.lib as lib

from maya import cmds
import maya.app.renderSetup.model.renderSetup as renderSetup


R_SINGLE_FRAME = re.compile(r"^(-?)\d+$")
R_FRAME_RANGE = re.compile(r"^(?P<sf>(-?)\d+)-(?P<ef>(-?)\d+)$")
R_FRAME_NUMBER = re.compile(r".+\.(?P<frame>[0-9]+)\..+")
R_LAYER_TOKEN = re.compile(
    r".*((?:%l)|(?:<layer>)|(?:<renderlayer>)).*", re.IGNORECASE
)
R_AOV_TOKEN = re.compile(r".*%a.*|.*<aov>.*|.*<renderpass>.*", re.IGNORECASE)
R_SUBSTITUTE_AOV_TOKEN = re.compile(r"%a|<aov>|<renderpass>", re.IGNORECASE)
R_REMOVE_AOV_TOKEN = re.compile(
    r"_%a|\.%a|_<aov>|\.<aov>|_<renderpass>|\.<renderpass>", re.IGNORECASE)
# to remove unused renderman tokens
R_CLEAN_FRAME_TOKEN = re.compile(r"\.?<f\d>\.?", re.IGNORECASE)
R_CLEAN_EXT_TOKEN = re.compile(r"\.?<ext>\.?", re.IGNORECASE)

R_SUBSTITUTE_LAYER_TOKEN = re.compile(
    r"%l|<layer>|<renderlayer>", re.IGNORECASE
)
R_SUBSTITUTE_CAMERA_TOKEN = re.compile(r"%c|<camera>", re.IGNORECASE)
R_SUBSTITUTE_SCENE_TOKEN = re.compile(r"%s|<scene>", re.IGNORECASE)

RENDERER_NAMES = {
    "mentalray": "MentalRay",
    "vray": "V-Ray",
    "arnold": "Arnold",
    "renderman": "Renderman",
    "redshift": "Redshift",
}

# not sure about the renderman image prefix
IMAGE_PREFIXES = {
    "mentalray": "defaultRenderGlobals.imageFilePrefix",
    "vray": "vraySettings.fileNamePrefix",
    "arnold": "defaultRenderGlobals.imageFilePrefix",
    "renderman": "rmanGlobals.imageFileFormat",
    "redshift": "defaultRenderGlobals.imageFilePrefix",
}


class ExpectedFiles:
    """Class grouping functionality for all supported renderers.

    Attributes:
        multipart (bool): Flag if multipart exrs are used.

    """

    multipart = False

    def __init__(self, render_instance):
        """Constructor."""
        self._render_instance = render_instance

    def get(self, renderer, layer):
        """Get expected files for given renderer and render layer.

        Args:
            renderer (str): Name of renderer
            layer (str): Name of render layer

        Returns:
            dict: Expected rendered files by AOV

        Raises:
            :exc:`UnsupportedRendererException`: If requested renderer
                is not supported. It needs to be implemented by extending
                :class:`AExpectedFiles` and added to this methods ``if``
                statement.

        """
        renderSetup.instance().switchToLayerUsingLegacyName(layer)

        if renderer.lower() == "arnold":
            return self._get_files(ExpectedFilesArnold(layer,
                                                       self._render_instance))
        if renderer.lower() == "vray":
            return self._get_files(ExpectedFilesVray(
                layer, self._render_instance))
        if renderer.lower() == "redshift":
            return self._get_files(ExpectedFilesRedshift(
                layer, self._render_instance))
        if renderer.lower() == "mentalray":
            return self._get_files(ExpectedFilesMentalray(
                layer, self._render_instance))
        if renderer.lower() == "renderman":
            return self._get_files(ExpectedFilesRenderman(
                layer, self._render_instance))

        raise UnsupportedRendererException(
            "unsupported {}".format(renderer)
        )

    def _get_files(self, renderer):
        files = renderer.get_files()
        self.multipart = renderer.multipart
        return files


@six.add_metaclass(ABCMeta)
class AExpectedFiles:
    """Abstract class with common code for all renderers.

    Attributes:
        renderer (str): name of renderer.
        layer (str): name of render layer.
        multipart (bool): flag for multipart exrs.

    """

    renderer = None
    layer = None
    multipart = False

    def __init__(self, layer, render_instance):
        """Constructor."""
        self.layer = layer
        self.render_instance = render_instance

    @abstractmethod
    def get_aovs(self):
        """To be implemented by renderer class."""

    @staticmethod
    def sanitize_camera_name(camera):
        """Sanitize camera name.

        Remove Maya illegal characters from camera name.

        Args:
            camera (str): Maya camera name.

        Returns:
            (str): sanitized camera name

        Example:
            >>> sanizite_camera_name('test:camera_01')
            test_camera_01

        """
        return re.sub('[^0-9a-zA-Z_]+', '_', camera)

    def get_renderer_prefix(self):
        """Return prefix for specific renderer.

        This is for most renderers the same and can be overriden if needed.

        Returns:
            str: String with image prefix containing tokens

        Raises:
            :exc:`UnsupportedRendererException`: If we requested image
                prefix for renderer we know nothing about.
                See :data:`IMAGE_PREFIXES` for mapping of renderers and
                image prefixes.

        """
        try:
            file_prefix = cmds.getAttr(IMAGE_PREFIXES[self.renderer])
        except KeyError:
            raise UnsupportedRendererException(
                "Unsupported renderer {}".format(self.renderer)
            )
        return file_prefix

    def _get_layer_data(self):
        #                      ______________________________________________
        # ____________________/ ____________________________________________/
        # 1 -  get scene name  /__________________/
        # ____________________/
        _, scene_basename = os.path.split(cmds.file(q=True, loc=True))
        scene_name, _ = os.path.splitext(scene_basename)

        file_prefix = self.get_renderer_prefix()

        if not file_prefix:
            raise RuntimeError("Image prefix not set")

        layer_name = self.layer
        if self.layer.startswith("rs_"):
            layer_name = self.layer[3:]

        scene_data = {
            "frameStart": int(self.get_render_attribute("startFrame")),
            "frameEnd": int(self.get_render_attribute("endFrame")),
            "frameStep": int(self.get_render_attribute("byFrameStep")),
            "padding": int(self.get_render_attribute("extensionPadding")),
            # if we have <camera> token in prefix path we'll expect output for
            # every renderable camera in layer.
            "cameras": self.get_renderable_cameras(),
            "sceneName": scene_name,
            "layerName": layer_name,
            "renderer": self.renderer,
            "defaultExt": cmds.getAttr("defaultRenderGlobals.imfPluginKey"),
            "filePrefix": file_prefix,
            "enabledAOVs": self.get_aovs(),
        }
        return scene_data

    def _generate_single_file_sequence(
            self, layer_data, force_aov_name=None):
        expected_files = []
        for cam in layer_data["cameras"]:
            file_prefix = layer_data["filePrefix"]
            mappings = (
                (R_SUBSTITUTE_SCENE_TOKEN, layer_data["sceneName"]),
                (R_SUBSTITUTE_LAYER_TOKEN, layer_data["layerName"]),
                (R_SUBSTITUTE_CAMERA_TOKEN, self.sanitize_camera_name(cam)),
                # this is required to remove unfilled aov token, for example
                # in Redshift
                (R_REMOVE_AOV_TOKEN, "") if not force_aov_name \
                else (R_SUBSTITUTE_AOV_TOKEN, force_aov_name),

                (R_CLEAN_FRAME_TOKEN, ""),
                (R_CLEAN_EXT_TOKEN, ""),
            )

            for regex, value in mappings:
                file_prefix = re.sub(regex, value, file_prefix)

            for frame in range(
                    int(layer_data["frameStart"]),
                    int(layer_data["frameEnd"]) + 1,
                    int(layer_data["frameStep"]),
            ):
                expected_files.append(
                    "{}.{}.{}".format(
                        file_prefix,
                        str(frame).rjust(layer_data["padding"], "0"),
                        layer_data["defaultExt"],
                    )
                )
        return expected_files

    def _generate_aov_file_sequences(self, layer_data):
        expected_files = []
        aov_file_list = {}
        for aov in layer_data["enabledAOVs"]:
            for cam in layer_data["cameras"]:
                file_prefix = layer_data["filePrefix"]

                mappings = (
                    (R_SUBSTITUTE_SCENE_TOKEN, layer_data["sceneName"]),
                    (R_SUBSTITUTE_LAYER_TOKEN, layer_data["layerName"]),
                    (R_SUBSTITUTE_CAMERA_TOKEN,
                     self.sanitize_camera_name(cam)),
                    (R_SUBSTITUTE_AOV_TOKEN, aov[0]),
                    (R_CLEAN_FRAME_TOKEN, ""),
                    (R_CLEAN_EXT_TOKEN, ""),
                )

                for regex, value in mappings:
                    file_prefix = re.sub(regex, value, file_prefix)

                aov_files = []
                for frame in range(
                        int(layer_data["frameStart"]),
                        int(layer_data["frameEnd"]) + 1,
                        int(layer_data["frameStep"]),
                ):
                    aov_files.append(
                        "{}.{}.{}".format(
                            file_prefix,
                            str(frame).rjust(layer_data["padding"], "0"),
                            aov[1],
                        )
                    )

                # if we have more then one renderable camera, append
                # camera name to AOV to allow per camera AOVs.
                aov_name = aov[0]
                if len(layer_data["cameras"]) > 1:
                    aov_name = "{}_{}".format(aov[0],
                                              self.sanitize_camera_name(cam))

                aov_file_list[aov_name] = aov_files
                file_prefix = layer_data["filePrefix"]

        expected_files.append(aov_file_list)
        return expected_files

    def get_files(self):
        """Return list of expected files.

        It will translate render token strings  ('<RenderPass>', etc.) to
        their values. This task is tricky as every renderer deals with this
        differently. It depends on `get_aovs()` abstract method implemented
        for every supported renderer.

        """
        layer_data = self._get_layer_data()

        expected_files = []
        if layer_data.get("enabledAOVs"):
            expected_files = self._generate_aov_file_sequences(layer_data)
        else:
            expected_files = self._generate_single_file_sequence(layer_data)

        return expected_files

    def get_renderable_cameras(self):
        """Get all renderable cameras.

        Returns:
            list: list of renderable cameras.

        """
        cam_parents = [
            cmds.listRelatives(x, ap=True)[-1] for x in cmds.ls(cameras=True)
        ]

        renderable_cameras = []
        for cam in cam_parents:
            if self.maya_is_true(cmds.getAttr("{}.renderable".format(cam))):
                renderable_cameras.append(cam)

        return renderable_cameras

    @staticmethod
    def maya_is_true(attr_val):
        """Whether a Maya attr evaluates to True.

        When querying an attribute value from an ambiguous object the
        Maya API will return a list of values, which need to be properly
        handled to evaluate properly.

        Args:
            attr_val (mixed): Maya attribute to be evaluated as bool.

        Returns:
            bool: cast Maya attribute to Pythons boolean value.

        """
        if isinstance(attr_val, types.BooleanType):
            return attr_val
        if isinstance(attr_val, (types.ListType, types.GeneratorType)):
            return any(attr_val)

        return bool(attr_val)

    @staticmethod
    def get_layer_overrides(attr):
        """Get overrides for attribute on given render layer.

        Args:
            attr (str): Maya attribute name.
            layer (str): Maya render layer name.

        Returns:
            Value of attribute override.

        """
        connections = cmds.listConnections(attr, plugs=True)
        if connections:
            for connection in connections:
                if connection:
                    # node_name = connection.split(".")[0]

                    attr_name = "%s.value" % ".".join(
                        connection.split(".")[:-1]
                    )
                    yield cmds.getAttr(attr_name)

    def get_render_attribute(self, attr):
        """Get attribute from render options.

        Args:
            attr (str): name of attribute to be looked up.

        Returns:
            Attribute value

        """
        return lib.get_attr_in_layer(
            "defaultRenderGlobals.{}".format(attr), layer=self.layer
        )


class ExpectedFilesArnold(AExpectedFiles):
    """Expected files for Arnold renderer.

    Attributes:
        aiDriverExtension (dict): Arnold AOV driver extension mapping.
            Is there a better way?
        renderer (str): name of renderer.

    """

    aiDriverExtension = {
        "jpeg": "jpg",
        "exr": "exr",
        "deepexr": "exr",
        "png": "png",
        "tiff": "tif",
        "mtoa_shaders": "ass",  # TODO: research what those last two should be
        "maya": "",
    }

    def __init__(self, layer, render_instance):
        """Constructor."""
        super(ExpectedFilesArnold, self).__init__(layer, render_instance)
        self.renderer = "arnold"

    def get_aovs(self):
        """Get all AOVs.

        See Also:
            :func:`AExpectedFiles.get_aovs()`

        Raises:
            :class:`AOVError`: If AOV cannot be determined.

        """
        enabled_aovs = []
        try:
            if not (
                    cmds.getAttr("defaultArnoldRenderOptions.aovMode")
                    and not cmds.getAttr("defaultArnoldDriver.mergeAOVs")  # noqa: W503, E501
            ):
                # AOVs are merged in mutli-channel file
                self.multipart = True
                return enabled_aovs
        except ValueError:
            # this occurs when Render Setting windows was not opened yet. In
            # such case there are no Arnold options created so query for AOVs
            # will fail. We terminate here as there are no AOVs specified then.
            # This state will most probably fail later on some Validator
            # anyway.
            return enabled_aovs

        # AOVs are set to be rendered separately. We should expect
        # <RenderPass> token in path.

        # handle aovs from references
        use_ref_aovs = self.render_instance.data.get(
            "useReferencedAovs", False) or False

        ai_aovs = cmds.ls(type="aiAOV")
        if not use_ref_aovs:
            ref_aovs = cmds.ls(type="aiAOV", referencedNodes=True)
            ai_aovs = list(set(ai_aovs) - set(ref_aovs))

        for aov in ai_aovs:
            enabled = self.maya_is_true(cmds.getAttr("{}.enabled".format(aov)))
            ai_driver = cmds.listConnections("{}.outputs".format(aov))[0]
            ai_translator = cmds.getAttr("{}.aiTranslator".format(ai_driver))
            try:
                aov_ext = self.aiDriverExtension[ai_translator]
            except KeyError:
                msg = (
                    "Unrecognized arnold " "driver format for AOV - {}"
                ).format(cmds.getAttr("{}.name".format(aov)))
                raise AOVError(msg)

            for override in self.get_layer_overrides(
                    "{}.enabled".format(aov)
            ):
                enabled = self.maya_is_true(override)
            if enabled:
                # If aov RGBA is selected, arnold will translate it to `beauty`
                aov_name = cmds.getAttr("%s.name" % aov)
                if aov_name == "RGBA":
                    aov_name = "beauty"
                enabled_aovs.append((aov_name, aov_ext))
        # Append 'beauty' as this is arnolds
        # default. If <RenderPass> token is specified and no AOVs are
        # defined, this will be used.
        enabled_aovs.append(
            (u"beauty", cmds.getAttr("defaultRenderGlobals.imfPluginKey"))
        )
        return enabled_aovs


class ExpectedFilesVray(AExpectedFiles):
    """Expected files for V-Ray renderer."""

    def __init__(self, layer, render_instance):
        """Constructor."""
        super(ExpectedFilesVray, self).__init__(layer, render_instance)
        self.renderer = "vray"

    def get_renderer_prefix(self):
        """Get image prefix for V-Ray.

        This overrides :func:`AExpectedFiles.get_renderer_prefix()` as
        we must add `<aov>` token manually.

        See also:
            :func:`AExpectedFiles.get_renderer_prefix()`

        """
        prefix = super(ExpectedFilesVray, self).get_renderer_prefix()
        prefix = "{}_<aov>".format(prefix)
        return prefix

    def _get_layer_data(self):
        """Override to get vray specific extension."""
        layer_data = super(ExpectedFilesVray, self)._get_layer_data()
        default_ext = cmds.getAttr("vraySettings.imageFormatStr")
        if default_ext in ["exr (multichannel)", "exr (deep)"]:
            default_ext = "exr"
        layer_data["defaultExt"] = default_ext
        layer_data["padding"] = cmds.getAttr("vraySettings.fileNamePadding")
        return layer_data

    def get_files(self):
        """Get expected files.

        This overrides :func:`AExpectedFiles.get_files()` as we
        we need to add one sequence for plain beauty if AOVs are enabled
        as vray output beauty without 'beauty' in filename.

        """
        expected_files = super(ExpectedFilesVray, self).get_files()

        layer_data = self._get_layer_data()
        # remove 'beauty' from filenames as vray doesn't output it
        update = {}
        if layer_data.get("enabledAOVs"):
            for aov, seqs in expected_files[0].items():
                if aov.startswith("beauty"):
                    new_list = []
                    for seq in seqs:
                        new_list.append(seq.replace("_beauty", ""))
                    update[aov] = new_list

            expected_files[0].update(update)
        return expected_files

    def get_aovs(self):
        """Get all AOVs.

        See Also:
            :func:`AExpectedFiles.get_aovs()`

        """
        enabled_aovs = []

        try:
            # really? do we set it in vray just by selecting multichannel exr?
            if (
                    cmds.getAttr("vraySettings.imageFormatStr")
                    == "exr (multichannel)"  # noqa: W503
            ):
                # AOVs are merged in mutli-channel file
                self.multipart = True
                return enabled_aovs
        except ValueError:
            # this occurs when Render Setting windows was not opened yet. In
            # such case there are no VRay options created so query for AOVs
            # will fail. We terminate here as there are no AOVs specified then.
            # This state will most probably fail later on some Validator
            # anyway.
            return enabled_aovs

        default_ext = cmds.getAttr("vraySettings.imageFormatStr")
        if default_ext in ["exr (multichannel)", "exr (deep)"]:
            default_ext = "exr"

        # add beauty as default
        enabled_aovs.append(
            (u"beauty", default_ext)
        )

        # handle aovs from references
        use_ref_aovs = self.render_instance.data.get(
            "useReferencedAovs", False) or False

        # this will have list of all aovs no matter if they are coming from
        # reference or not.
        vr_aovs = cmds.ls(
            type=["VRayRenderElement", "VRayRenderElementSet"]) or []
        if not use_ref_aovs:
            ref_aovs = cmds.ls(
                type=["VRayRenderElement", "VRayRenderElementSet"],
                referencedNodes=True) or []
            # get difference
            vr_aovs = list(set(vr_aovs) - set(ref_aovs))

        for aov in vr_aovs:
            enabled = self.maya_is_true(cmds.getAttr("{}.enabled".format(aov)))
            for override in self.get_layer_overrides(
                    "{}.enabled".format(aov)
            ):
                enabled = self.maya_is_true(override)

            if enabled:
                enabled_aovs.append(
                    (self._get_vray_aov_name(aov), default_ext))

        return enabled_aovs

    @staticmethod
    def _get_vray_aov_name(node):
        """Get AOVs name from Vray.

        Args:
            node (str): aov node name.

        Returns:
            str: aov name.

        """
        vray_name = None
        vray_explicit_name = None
        vray_file_name = None
        for attr in cmds.listAttr(node):
            if attr.startswith("vray_filename"):
                vray_file_name = cmds.getAttr("{}.{}".format(node, attr))
            elif attr.startswith("vray_name"):
                vray_name = cmds.getAttr("{}.{}".format(node, attr))
            elif attr.startswith("vray_explicit_name"):
                vray_explicit_name = cmds.getAttr("{}.{}".format(node, attr))

            if vray_file_name is not None and vray_file_name != "":
                final_name = vray_file_name
            elif vray_explicit_name is not None and vray_explicit_name != "":
                final_name = vray_explicit_name
            elif vray_name is not None and vray_name != "":
                final_name = vray_name
            else:
                continue
            # special case for Material Select elements - these are named
            # based on the materia they are connected to.
            if "vray_mtl_mtlselect" in cmds.listAttr(node):
                connections = cmds.listConnections(
                    "{}.vray_mtl_mtlselect".format(node))
                if connections:
                    final_name += '_{}'.format(str(connections[0]))

            return final_name


class ExpectedFilesRedshift(AExpectedFiles):
    """Expected files for Redshift renderer.

    Attributes:
        ext_mapping (list): Mapping redshift extension dropdown values
            to strings.

        unmerged_aovs (list): Name of aovs that are not merged into resulting
            exr and we need them specified in expectedFiles output.

    """

    unmerged_aovs = ["Cryptomatte"]

    ext_mapping = ["iff", "exr", "tif", "png", "tga", "jpg"]

    def __init__(self, layer, render_instance):
        """Construtor."""
        super(ExpectedFilesRedshift, self).__init__(layer, render_instance)
        self.renderer = "redshift"

    def get_renderer_prefix(self):
        """Get image prefix for Redshift.

        This overrides :func:`AExpectedFiles.get_renderer_prefix()` as
        we must add `<aov>` token manually.

        See also:
            :func:`AExpectedFiles.get_renderer_prefix()`

        """
        prefix = super(ExpectedFilesRedshift, self).get_renderer_prefix()
        prefix = "{}.<aov>".format(prefix)
        return prefix

    def get_files(self):
        """Get expected files.

        This overrides :func:`AExpectedFiles.get_files()` as we
        we need to add one sequence for plain beauty if AOVs are enabled
        as vray output beauty without 'beauty' in filename.

        """
        expected_files = super(ExpectedFilesRedshift, self).get_files()
        layer_data = self._get_layer_data()

        # Redshift doesn't merge Cryptomatte AOV to final exr. We need to check
        # for such condition and add it to list of expected files.

        for aov in layer_data.get("enabledAOVs"):
            if aov[0].lower() == "cryptomatte":
                aov_name = aov[0]
                expected_files.append(
                    {aov_name: self._generate_single_file_sequence(layer_data)}
                )

        if layer_data.get("enabledAOVs"):
            # because if Beauty is added manually, it will be rendered as
            # 'Beauty_other' in file name and "standard" beauty will have
            # 'Beauty' in its name. When disabled, standard output will be
            # without `Beauty`.
            if expected_files[0].get(u"Beauty"):
                expected_files[0][u"Beauty_other"] = expected_files[0].pop(
                    u"Beauty")
                new_list = [
                    seq.replace(".Beauty", ".Beauty_other")
                    for seq in expected_files[0][u"Beauty_other"]
                ]

                expected_files[0][u"Beauty_other"] = new_list
                expected_files[0][u"Beauty"] = self._generate_single_file_sequence(  # noqa: E501
                    layer_data, force_aov_name="Beauty"
                )
            else:
                expected_files[0][u"Beauty"] = self._generate_single_file_sequence(  # noqa: E501
                    layer_data
                )

        return expected_files

    def get_aovs(self):
        """Get all AOVs.

        See Also:
            :func:`AExpectedFiles.get_aovs()`

        """
        enabled_aovs = []

        try:
            if self.maya_is_true(
                    cmds.getAttr("redshiftOptions.exrForceMultilayer")
            ):
                # AOVs are merged in mutli-channel file
                self.multipart = True
                return enabled_aovs
        except ValueError:
            # this occurs when Render Setting windows was not opened yet. In
            # such case there are no Redshift options created so query for AOVs
            # will fail. We terminate here as there are no AOVs specified then.
            # This state will most probably fail later on some Validator
            # anyway.
            return enabled_aovs

        default_ext = self.ext_mapping[
            cmds.getAttr("redshiftOptions.imageFormat")
        ]
        rs_aovs = cmds.ls(type="RedshiftAOV", referencedNodes=False)

        # todo: find out how to detect multichannel exr for redshift
        for aov in rs_aovs:
            enabled = self.maya_is_true(cmds.getAttr("{}.enabled".format(aov)))
            for override in self.get_layer_overrides(
                    "{}.enabled".format(aov)
            ):
                enabled = self.maya_is_true(override)

            if enabled:
                # If AOVs are merged into multipart exr, append AOV only if it
                # is in the list of AOVs that renderer cannot (or will not)
                # merge into final exr.
                if self.maya_is_true(
                        cmds.getAttr("redshiftOptions.exrForceMultilayer")
                ):
                    if cmds.getAttr("%s.name" % aov) in self.unmerged_aovs:
                        enabled_aovs.append(
                            (cmds.getAttr("%s.name" % aov), default_ext)
                        )
                else:
                    enabled_aovs.append(
                        (cmds.getAttr("%s.name" % aov), default_ext)
                    )

        if self.maya_is_true(
                cmds.getAttr("redshiftOptions.exrForceMultilayer")
        ):
            # AOVs are merged in mutli-channel file
            self.multipart = True

        return enabled_aovs


class ExpectedFilesRenderman(AExpectedFiles):
    """Expected files for Renderman renderer.

    Warning:
        This is very rudimentary and needs more love and testing.
    """

    def __init__(self, layer, render_instance):
        """Constructor."""
        super(ExpectedFilesRenderman, self).__init__(layer, render_instance)
        self.renderer = "renderman"

    def get_aovs(self):
        """Get all AOVs.

        See Also:
            :func:`AExpectedFiles.get_aovs()`

        """
        enabled_aovs = []

        default_ext = "exr"
        displays = cmds.listConnections("rmanGlobals.displays")
        for aov in displays:
            aov_name = str(aov)
            if aov_name == "rmanDefaultDisplay":
                aov_name = "beauty"

            enabled = self.maya_is_true(cmds.getAttr("{}.enable".format(aov)))
            for override in self.get_layer_overrides(
                    "{}.enable".format(aov)
            ):
                enabled = self.maya_is_true(override)

            if enabled:
                enabled_aovs.append((aov_name, default_ext))

        return enabled_aovs

    def get_files(self):
        """Get expected files.

        This overrides :func:`AExpectedFiles.get_files()` as we
        we need to add one sequence for plain beauty if AOVs are enabled
        as vray output beauty without 'beauty' in filename.

        In renderman we hack it with prepending path. This path would
        normally be translated from `rmanGlobals.imageOutputDir`. We skip
        this and hardcode prepend path we expect. There is no place for user
        to mess around with this settings anyway and it is enforced in
        render settings validator.
        """
        layer_data = self._get_layer_data()
        new_aovs = {}

        expected_files = super(ExpectedFilesRenderman, self).get_files()
        # we always get beauty
        for aov, files in expected_files[0].items():
            new_files = []
            for file in files:
                new_file = "{}/{}/{}".format(
                    layer_data["sceneName"], layer_data["layerName"], file
                )
                new_files.append(new_file)
            new_aovs[aov] = new_files

        return [new_aovs]


class ExpectedFilesMentalray(AExpectedFiles):
    """Skeleton unimplemented class for Mentalray renderer."""

    def __init__(self, layer, render_instance):
        """Constructor.

        Raises:
            :exc:`UnimplementedRendererException`: as it is not implemented.

        """
        super(ExpectedFilesMentalray, self).__init__(layer, render_instance)
        raise UnimplementedRendererException("Mentalray not implemented")

    def get_aovs(self):
        """Get all AOVs.

        See Also:
            :func:`AExpectedFiles.get_aovs()`

        """
        return []


class AOVError(Exception):
    """Custom exception for determining AOVs."""


class UnsupportedRendererException(Exception):
    """Custom exception.

    Raised when requesting data from unsupported renderer.
    """


class UnimplementedRendererException(Exception):
    """Custom exception.

    Raised when requesting data from renderer that is not implemented yet.
    """
