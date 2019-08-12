from avalon import api
import pype.maya.plugin
import os
from pypeapp import config
import pymel.core as pm
reload(config)


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

            groupNode = pm.PyNode(groupName)
            roots = set()
            print(nodes)

            for node in nodes:
                try:
                    roots.add(pm.PyNode(node).getAllParents()[-2])
                except:
                    pass
            for root in roots:
                root.setParent(world=True)

            groupNode.root().zeroTransformPivots()
            for root in roots:
                root.setParent(groupNode)

            presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
            colors = presets['plugins']['maya']['load']['colors']
            c = colors.get(family)
            if c is not None:
                groupNode.useOutlinerColor.set(1)
                groupNode.outlinerColor.set(c[0], c[1], c[2])

            self[:] = nodes

            return nodes

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
