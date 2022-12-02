# -*- coding: utf-8 -*-
"""Library of classes and functions deadling with MtoA functionality."""
import tempfile
import contextlib

import clique
import pyblish.api

from maya import cmds

from openpype.pipeline import publish
from .viewport import vp2_paused_context
from .lib import selection


class _AssExtractor(publish.Extractor):
    """Base class for ASS type extractors."""

    order = pyblish.api.ExtractorOrder + 0.01
    hosts = ["maya"]

    def get_ass_export_mask(self, maya_set):
        import arnold  # noqa
        mask = arnold.AI_NODE_ALL

        ai_masks = {"options": {"value": arnold.AI_NODE_OPTIONS,
                                "default": False},
                    "camera": {"value": arnold.AI_NODE_CAMERA,
                               "default": False},
                    "light": {"value": arnold.AI_NODE_LIGHT,
                              "default": False},
                    "shape": {"value": arnold.AI_NODE_SHAPE,
                              "default": True},
                    "shader": {"value": arnold.AI_NODE_SHADER,
                               "default": True},
                    "override": {"value": arnold.AI_NODE_OVERRIDE,
                                 "default": False},
                    "driver": {"value": arnold.AI_NODE_DRIVER,
                               "default": False},
                    "filter": {"value": arnold.AI_NODE_FILTER,
                               "default": False},
                    "color_manager": {"value": arnold.AI_NODE_COLOR_MANAGER,
                                      "default": True},
                    "operator": {"value": arnold.AI_NODE_OPERATOR,
                                 "default": True}}

        for mask_name, mask_data in ai_masks.items():
            attr = "inf_ass_export_{}".format(mask_name)

            submask = self.get_set_attr("{}.{}".format(maya_set, attr),
                                        default=mask_data["default"])

            if not submask:
                mask = mask ^ mask_data["value"]

        return mask

    def process(self, instance):
        #What is a dry run?
        #ass.rr seems like an abstract variable. Needs clarification.
        dry_run = instance.data.get("ass.rr")

        staging_dir = self.staging_dir(instance)
        sequence = instance.data.get("exportSequence", False)

        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            cmds.loadPlugin("mtoa")

        # Export to a temporal path
        export_dir = instance.context.data["stagingDir"]
        export_path = tempfile.NamedTemporaryFile(suffix=".ass",
                                                  dir=export_dir,
                                                  delete=False)

        set_ = instance.data["set"]
        kwargs = {"shadowLinks": 1,
                  "lightLinks": 1,
                  "boundingBox": True,
                  "selected": True,
                  "f": export_path.name}

        # Animation

        if sequence:
            mask = self.get_ass_export_mask(set_)
            start = instance.data.get("frameStartHandle", 1)
            end = instance.data.get("frameEndHandle", 1)
            step = instance.data.get("step", 1.0)
            if start is not None:
                kwargs["startFrame"] = float(start)
                kwargs["endFrame"] = float(end)
                kwargs["frameStep"] = float(step)
        else:
            mask = 44

        #get/set should be plugin options.
        # Generic options
        if self.get_set_attr("{}.inf_ass_expand_procedurals".format(set_),
                             False):
            kwargs["expandProcedurals"] = True

        if self.get_set_attr("{}.inf_ass_fullpath".format(set_),
                             True):
            kwargs["fullPath"] = True

        kwargs["mask"] = mask

        # Motion blur
        mb = self.get_set_attr("{}.inf_ass_motion_blur".format(set_), False)
        keys = self.get_set_attr("{}.inf_ass_mb_keys".format(set_), -1)
        length = self.get_set_attr("{}.inf_ass_mb_length".format(set_), -1)

        #Targets should already be collected
        targets = self.get_targets(instance)

        _sorted_kwargs = sorted(kwargs.items(), key=lambda x: x[0])
        _sorted_kwargs = ["{}={!r}".format(x, y) for x, y in _sorted_kwargs]

        if not dry_run:
            self.log.debug("Running command: cmds.arnoldExportAss({})"
                           .format(", ".join(_sorted_kwargs)))
            #There should be a context for not updating the viewport from
            #pointcache extraction.
            with vp2_paused_context():
                with selection(targets):
                    with self.motion_blur_ctx(mb, keys, length):
                        result = cmds.arnoldExportAss(**kwargs)
        else:
            instance.data["assExportKwargs"] = kwargs
            start = kwargs.get("startFrame")
            end = kwargs.get("endFrame")
            result = []

            range_ = [0]
            if start is not None:
                range_ = range(int(start), int(end) + 1)

            for i in range_:
                #padding amount should be configurable. 3 does not seems
                #enough as default.
                fp = "{}.{:03d}.ass".format(export_path.name, i)
                with open(fp, "w"):
                    pass
                result.append(fp)

        #Whether its a sequence or not, should already have been determined.
        if len(result) == 1:
            filepath = result[0]
        else:
            collection = clique.assemble(result)[0][0]
            filepath = collection.format()

        # Register the file
        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'ass',
            'ext': 'ass',
            'files': filepath,
            "stagingDir": staging_dir
        }

        instance.data["representations"].append(representation)

    @contextlib.contextmanager
    def motion_blur_ctx(self, force, keys, length):
        if not force:
            yield
            return

        cmb = cmds.getAttr("defaultArnoldRenderOptions.motion_blur_enable")
        ckeys = cmds.getAttr("defaultArnoldRenderOptions.motion_steps")
        clen = cmds.getAttr("defaultArnoldRenderOptions.motion_frames")

        cmds.setAttr("defaultArnoldRenderOptions.motion_blur_enable", 1)
        if keys > 0:
            cmds.setAttr("defaultArnoldRenderOptions.motion_steps", keys)
        if length >= 0:
            cmds.setAttr("defaultArnoldRenderOptions.motion_frames", length)

        try:
            yield
        finally:
            cmds.setAttr("defaultArnoldRenderOptions.motion_blur_enable", cmb)
            cmds.setAttr("defaultArnoldRenderOptions.motion_steps", ckeys)
            cmds.setAttr("defaultArnoldRenderOptions.motion_frames", clen)
