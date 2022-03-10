import os
from maya import cmds
from avalon import api
from openpype.api import get_project_settings
from openpype.lib import get_creator_by_name
from openpype.pipeline import legacy_create
import openpype.hosts.maya.api.plugin
from openpype.hosts.maya.api.lib import maintained_selection


class ReferenceLoader(openpype.hosts.maya.api.plugin.ReferenceLoader):
    """Load the model"""

    families = ["model",
                "pointcache",
                "animation",
                "mayaAscii",
                "mayaScene",
                "setdress",
                "layout",
                "camera",
                "rig",
                "camerarig",
                "xgen"]
    representations = ["ma", "abc", "fbx", "mb"]

    label = "Reference"
    order = -10
    icon = "code-fork"
    color = "orange"

    # Name of creator class that will be used to create animation instance
    animation_creator_name = "CreateAnimation"

    def process_reference(self, context, name, namespace, options):
        import maya.cmds as cmds
        import pymel.core as pm

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "model"

        group_name = "{}:_GRP".format(namespace)
        # True by default to keep legacy behaviours
        attach_to_root = options.get("attach_to_root", True)

        with maintained_selection():
            cmds.loadPlugin("AbcImport.mll", quiet=True)
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              sharedReferenceFile=False,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=attach_to_root,
                              groupName=group_name)

            shapes = cmds.ls(nodes, shapes=True, long=True)

            new_nodes = (list(set(nodes) - set(shapes)))

            current_namespace = pm.namespaceInfo(currentNamespace=True)

            if current_namespace != ":":
                group_name = current_namespace + ":" + group_name

            group_name = "|" + group_name

            self[:] = new_nodes

            if attach_to_root:
                group_node = pm.PyNode(group_name)
                roots = set()

                for node in new_nodes:
                    try:
                        roots.add(pm.PyNode(node).getAllParents()[-2])
                    except:  # noqa: E722
                        pass

                if family not in ["layout", "setdress",
                                  "mayaAscii", "mayaScene"]:
                    for root in roots:
                        root.setParent(world=True)

                group_node.zeroTransformPivots()
                for root in roots:
                    root.setParent(group_node)

                cmds.setAttr(group_name + ".displayHandle", 1)

                settings = get_project_settings(os.environ['AVALON_PROJECT'])
                colors = settings['maya']['load']['colors']
                c = colors.get(family)
                if c is not None:
                    group_node.useOutlinerColor.set(1)
                    group_node.outlinerColor.set(
                        (float(c[0]) / 255),
                        (float(c[1]) / 255),
                        (float(c[2]) / 255))

                cmds.setAttr(group_name + ".displayHandle", 1)
                # get bounding box
                bbox = cmds.exactWorldBoundingBox(group_name)
                # get pivot position on world space
                pivot = cmds.xform(group_name, q=True, sp=True, ws=True)
                # center of bounding box
                cx = (bbox[0] + bbox[3]) / 2
                cy = (bbox[1] + bbox[4]) / 2
                cz = (bbox[2] + bbox[5]) / 2
                # add pivot position to calculate offset
                cx = cx + pivot[0]
                cy = cy + pivot[1]
                cz = cz + pivot[2]
                # set selection handle offset to center of bounding box
                cmds.setAttr(group_name + ".selectHandleX", cx)
                cmds.setAttr(group_name + ".selectHandleY", cy)
                cmds.setAttr(group_name + ".selectHandleZ", cz)

            if family == "rig":
                self._post_process_rig(name, namespace, context, options)
            else:

                if "translate" in options:
                    cmds.setAttr(group_name + ".t", *options["translate"])

            return new_nodes

    def switch(self, container, representation):
        self.update(container, representation)

    def _post_process_rig(self, name, namespace, context, options):

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

        self.log.info("Creating subset: {}".format(namespace))

        # Create the animation instance
        creator_plugin = get_creator_by_name(self.animation_creator_name)
        with maintained_selection():
            cmds.select([output, controls] + roots, noExpand=True)
            legacy_create(
                creator_plugin,
                name=namespace,
                asset=asset,
                options={"useSelection": True},
                data={"dependencies": dependency}
            )
