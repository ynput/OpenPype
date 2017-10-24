from maya import cmds

import colorbleed.maya.plugin
from avalon import api, maya


class RigLoader(colorbleed.maya.plugin.ReferenceLoader):
    """Specific loader for rigs

    This automatically creates an instance for animators upon load.

    """

    families = ["colorbleed.rig"]
    representations = ["ma"]

    label = "Reference rig"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          reference=True,
                          returnNewNodes=True,
                          groupReference=True,
                          groupName="{}:{}".format(namespace, name))

        # Store for post-process
        self[:] = nodes
        if data.get("post_process", True):
            self._post_process(name, namespace, context, data)

        return nodes

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
                       family="colorbleed.animation",
                       options={"useSelection": True},
                       data={"dependencies": dependency})
