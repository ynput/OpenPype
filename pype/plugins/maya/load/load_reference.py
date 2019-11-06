import pype.maya.plugin
import os
from pypeapp import config
reload(config)
import pype.maya.plugin
reload(pype.maya.plugin)

class ReferenceLoader(pype.maya.plugin.ReferenceLoader):
    """Load the model"""

    families = ["model", "pointcache", "animation"]
    representations = ["ma", "abc"]
    tool_names = ["loader"]

    label = "Reference"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):
        import maya.cmds as cmds
        from avalon import maya
        import pymel.core as pm


        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "model"

        with maya.maintained_selection():

            groupName = "{}:{}".format(namespace, name)
            cmds.loadPlugin("AbcImport.mll", quiet=True)
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              sharedReferenceFile=False,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name),
                              reference=True,
                              returnNewNodes=True)

            namespace = cmds.referenceQuery(nodes[0], namespace=True)

            shapes = cmds.ls(nodes, shapes=True, long=True)
            print(shapes)

            newNodes = (list(set(nodes) - set(shapes)))
            print(newNodes)

            groupNode = pm.PyNode(groupName)
            roots = set()
            print(nodes)

            for node in newNodes:
                try:
                    roots.add(pm.PyNode(node).getAllParents()[-2])
                except:
                    pass
            for root in roots:
                root.setParent(world=True)

            groupNode.root().zeroTransformPivots()
            for root in roots:
                root.setParent(groupNode)

            cmds.setAttr(groupName + ".displayHandle", 1)

            presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
            colors = presets['plugins']['maya']['load']['colors']
            c = colors.get(family)
            if c is not None:
                groupNode.useOutlinerColor.set(1)
                groupNode.outlinerColor.set(c[0], c[1], c[2])

            self[:] = newNodes

            cmds.setAttr(groupName + ".displayHandle", 1)
            # get bounding box
            bbox = cmds.exactWorldBoundingBox(groupName)
            # get pivot position on world space
            pivot = cmds.xform(groupName, q=True, sp=True, ws=True)
            # center of bounding box
            cx = (bbox[0] + bbox[3]) / 2
            cy = (bbox[1] + bbox[4]) / 2
            cz = (bbox[2] + bbox[5]) / 2
            # add pivot position to calculate offset
            cx = cx + pivot[0]
            cy = cy + pivot[1]
            cz = cz + pivot[2]
            # set selection handle offset to center of bounding box
            cmds.setAttr(groupName + ".selectHandleX", cx)
            cmds.setAttr(groupName + ".selectHandleY", cy)
            cmds.setAttr(groupName + ".selectHandleZ", cz)

            return newNodes

    def switch(self, container, representation):
        self.update(container, representation)


# for backwards compatibility
class AbcLoader(ReferenceLoader):
    label = "Deprecated loader (don't use)"
    families = ["pointcache", "animation"]
    representations = ["abc"]
    tool_names = []


# for backwards compatibility
class ModelLoader(ReferenceLoader):
    label = "Deprecated loader (don't use)"
    families = ["model", "pointcache"]
    representations = ["abc"]
    tool_names = []
