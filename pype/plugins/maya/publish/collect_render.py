import re

from maya import cmds
from maya import OpenMaya as om

import maya.app.renderSetup.model.renderSetup as renderSetup

import pyblish.api

from avalon import maya, api
import pype.maya.lib as lib


class CollectMayaRender(pyblish.api.InstancePlugin):
    """Gather all publishable render layers from renderSetup"""

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["maya"]
    label = "Collect Render Layers"
    families = ["render"]

    def process(self, instance):
        collected_render_layers = instance.data['setMembers']

        self._rs = renderSetup.instance()
        maya_render_layers = {l.name(): l for l in self._rs.getRenderLayers()}

        self.maya_layers = maya_render_layers

        for layer in collected_render_layers:
            # every layer in set should start with `LAYER_` prefix
            try:
                expected_layer_name = re.search(r"^LAYER_(.*)", layer).group(1)
            except IndexError:
                msg = ("Invalid layer name in set [ {} ]".format(layer))
                self.log.warnig(msg)
                continue

            # check if layer is part of renderSetup
            if expected_layer_name not in maya_render_layers:
                msg = ("Render layer [ {} ] is not in "
                       "Render Setup".format(expected_layer_name))
                self.log.warning(msg)
                continue

            # check if layer is renderable
            if not maya_render_layers[expected_layer_name].isRenderable():
                msg = ("Render layer [ {} ] is not "
                       "renderable".format(expected_layer_name))
                self.log.warning(msg)
                continue

            # test if there are sets (subsets) to attach render to
            sets = cmds.ls(expected_layer_name, long=True, dag=True, sets=True)
            self.log.debug(sets)

            # Get layer specific settings, might be overrides
            data = {
                "subset": expected_layer_name,
                "setMembers": layer,
                "publish": True,
                "frameStart": self.get_render_attribute("startFrame",
                                                        layer=layer),
                "frameEnd": self.get_render_attribute("endFrame",
                                                      layer=layer),
                "byFrameStep": self.get_render_attribute("byFrameStep",
                                                         layer=layer),
                "renderer": self.get_render_attribute("currentRenderer",
                                                      layer=layer),

                # instance subset
                "family": "Render Layers",
                "families": ["renderlayer"],
                "asset": asset,
                "time": api.time(),
                "author": context.data["user"],

                # Add source to allow tracing back to the scene from
                # which was submitted originally
                "source": filepath
            }

            # Apply each user defined attribute as data
            for attr in cmds.listAttr(layer, userDefined=True) or list():
                try:
                    value = cmds.getAttr("{}.{}".format(layer, attr))
                except Exception:
                    # Some attributes cannot be read directly,
                    # such as mesh and color attributes. These
                    # are considered non-essential to this
                    # particular publishing pipeline.
                    value = None

                data[attr] = value

            # Include (optional) global settings
            # TODO(marcus): Take into account layer overrides
            # Get global overrides and translate to Deadline values
            overrides = self.parse_options(render_globals)
            data.update(**overrides)

            # Define nice label
            label = "{0} ({1})".format(layername, data["asset"])
            label += "  [{0}-{1}]".format(int(data["frameStart"]),
                                          int(data["frameEnd"]))

            instance = context.create_instance(layername)
            instance.data["label"] = label
            instance.data.update(data)
        pass

    def get_attributes(self, layer, attribute):

        pass

    def _get_overrides(self, layer):
        rset = self.maya_layers[layer].renderSettingsCollectionInstance()
        return rset.getOverrides()
