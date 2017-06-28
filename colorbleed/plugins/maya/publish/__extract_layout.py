import json

from maya import cmds

import avalon.maya
import colorbleed.api

import cb.utils.maya.context as context
import cbra.utils.maya.layout as layout


def get_upstream_hierarchy_fast(nodes):
    """Passed in nodes must be long names!"""

    matched = set()
    parents = []

    for node in nodes:
        hierarchy = node.split("|")
        num = len(hierarchy)
        for x in range(1, num-1):
            parent = "|".join(hierarchy[:num-x])
            if parent in parents:
                break
            else:
                parents.append(parent)
                matched.add(parent)

    return parents


class ExtractLayout(colorbleed.api.Extractor):
    """Extract Layout as both gpuCache and Alembic"""

    label = "Layout (gpuCache & alembic)"
    hosts = ["maya"]
    families = ["colorbleed.layout"]

    def process(self, instance):

        # Define extract output file path
        dir_path = self.staging_dir(instance)

        start = instance.data.get("startFrame", 1)
        end = instance.data.get("endFrame", 1)
        step = instance.data.get("step", 1.0)
        placeholder = instance.data.get("placeholder", False)
        write_color_sets = instance.data.get("writeColorSets", False)
        renderable_only = instance.data.get("renderableOnly", False)
        visible_only = instance.data.get("visibleOnly", False)

        layers = instance.data.get("animLayersActive", None)
        if layers:
            layers = json.loads(layers)
            self.log.info("Publishing with animLayers active: "
                          "{0}".format(layers))

        # Perform extraction
        self.log.info("Performing extraction..")
        with avalon.maya.maintained_selection():

            # Get children hierarchy
            nodes = instance.data['setMembers']
            cmds.select(nodes, r=True, hierarchy=True)
            hierarchy = cmds.ls(selection=True, long=True)

            with context.evaluation("off"):
                with context.no_refresh():
                    with context.active_anim_layers(layers):
                        layout.extract_layout(hierarchy,
                                              dir_path,
                                              start=start,
                                              end=end,
                                              step=step,
                                              placeholder=placeholder,
                                              write_color_sets=write_color_sets,
                                              renderable_only=renderable_only,
                                              visible_only=visible_only)

        self.log.info("Extracted instance '{0}' to: {1}".format(
            instance.name, dir_path))
