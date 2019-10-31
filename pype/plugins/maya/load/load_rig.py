from maya import cmds

import pype.maya.plugin
from avalon import api, maya
import os
from pypeapp import config


class RigLoader(pype.maya.plugin.ReferenceLoader):
    """Specific loader for rigs

    This automatically creates an instance for animators upon load.

    """

    families = ["rig"]
    representations = ["ma"]

    label = "Reference rig"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "rig"

        groupName = "{}:{}".format(namespace, name)
        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          reference=True,
                          returnNewNodes=True,
                          groupReference=True,
                          groupName=groupName)

        cmds.xform(groupName, pivots=(0, 0, 0))

        presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
        colors = presets['plugins']['maya']['load']['colors']

        c = colors.get(family)
        if c is not None:
            cmds.setAttr(groupName + ".useOutlinerColor", 1)
            cmds.setAttr(groupName + ".outlinerColor",
                         c[0], c[1], c[2])

        shapes = cmds.ls(nodes, shapes=True, long=True)
        print(shapes)

        newNodes = (list(set(nodes) - set(shapes)))
        print(newNodes)

        # Store for post-process
        self[:] = newNodes
        if data.get("post_process", True):
            self._post_process(name, namespace, context, data)

        return newNodes

    def _post_process(self, name, namespace, context, data):

        # TODO(marcus): We are hardcoding the name "out_SET" here.
        #   Better register this keyword, so that it can be used
        #   elsewhere, such as in the Integrator plug-in,
        #   without duplication.

        output = next((node for node in self if
                       node.endswith("out_SET")), None)
        controls = next((node for node in self if
                         node.endswith("controls_SET")), None)

        assert output, "No out_SET in rig, this is a bug."
        assert controls, "No controls_SET in rig, this is a bug."

        # Find the roots amongst the loaded nodes
        roots = cmds.ls(self[:], assemblies=True, long=True)
        assert roots, "No root nodes in rig, this is a bug."

        asset = api.Session["AVALON_ASSET"]
        dependency = str(context["representation"]["_id"])

        # Create the animation instance
        with maya.maintained_selection():
            cmds.select([output, controls] + roots, noExpand=True)
            api.create(name=namespace,
                       asset=asset,
                       family="animation",
                       options={"useSelection": True},
                       data={"dependencies": dependency})

    def switch(self, container, representation):
        self.update(container, representation)
