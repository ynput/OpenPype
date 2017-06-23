from maya import cmds
from avalon import api


class RigLoader(api.Loader):
    """Specific loader for rigs

    This automatically creates an instance for animators upon load.

    """

    families = ["colorbleed.rig"]
    representations = ["ma"]

    def process(self, name, namespace, context):
        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          reference=True,
                          returnNewNodes=True,
                          groupReference=True,
                          groupName=namespace + ":" + name)

        # Store for post-process
        self[:] = nodes

    def post_process(self, name, namespace, context):
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

        with maya.maintained_selection():
            cmds.select([output, controls], noExpand=True)

            dependencies = [context["representation"]["_id"]]
            asset = context["asset"]["name"] + "_"

            # TODO(marcus): Hardcoding the family here, better separate this.
            maya.create(
                name=maya.unique_name(asset, suffix="_SET"),
                asset=context["asset"]["name"],
                family="avalon.animation",
                options={"useSelection": True},
                data={
                    "dependencies": " ".join(str(d) for d in dependencies)
                })
