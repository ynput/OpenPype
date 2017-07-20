import os

from maya import cmds

from avalon import api


class RigLoader(api.Loader):
    """Specific loader for rigs

    This automatically creates an instance for animators upon load.

    """

    families = ["colorbleed.rig"]
    representations = ["ma"]

    label = "Reference rig"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):
        print("debug : {}\n{}\n".format(name, namespace))
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

    def _post_process(self, name, namespace, context, data):
        from avalon import maya

        # TODO(marcus): We are hardcoding the name "out_SET" here.
        #   Better register this keyword, so that it can be used
        #   elsewhere, such as in the Integrator plug-in,
        #   without duplication.

        output = next(
            (node for node in self
                if node.endswith("out_SET")), None)
        controls = next(
            (node for node in self
                if node.endswith("controls_SET")), None)

        assert output, "No out_SET in rig, this is a bug."
        assert controls, "No controls_SET in rig, this is a bug."

        # To ensure the asset under which is published is actually the shot
        # not the asset to which the rig belongs to.
        current_task = os.environ["AVALON_TASK"]
        asset_name = context["asset"]["name"]
        if current_task == "animate":
            asset = "{}".format(os.environ["AVALON_ASSET"])
        else:
            asset = "{}".format(asset_name)

        with maya.maintained_selection():
            cmds.select([output, controls], noExpand=True)

            # TODO(marcus): Hardcoding the family here, better separate this.
            dependencies = [context["representation"]["_id"]]
            dependencies = " ".join(str(d) for d in dependencies)
            unique_name = maya.unique_name(asset_name, suffix="_SET")

            maya.create(name=unique_name,
                        asset=asset,
                        family="colorbleed.animation",
                        options={"useSelection": True},
                        data={"dependencies": dependencies})
