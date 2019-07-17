from avalon import api
import pype.maya.plugin
import os
from pypeapp import config
reload(config)


class ModelLoader(pype.maya.plugin.ReferenceLoader):
    """Load the model"""

    families = ["model"]
    representations = ["ma", "abc"]
    tool_names = ["loader"]

    label = "Reference Model"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
        from avalon import maya

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

            nodes.pop(1)
            roots = set()
            for node in nodes:
                try:
                    roots.add(cmds.ls(node, long=True)[0].split('|')[2])
                except:
                    pass
            cmds.parent(roots, world=True)
            cmds.makeIdentity(groupName, apply=False, rotate=True,
                              translate=True, scale=True)
            cmds.parent(roots, groupName)

            nodes.append(groupName)

            presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
            colors = presets['plugins']['maya']['load']['colors']
            c = colors.get('model')
            if c is not None:
                cmds.setAttr(groupName + ".useOutlinerColor", 1)
                cmds.setAttr(groupName + ".outlinerColor",
                             c[0], c[1], c[2])

            self[:] = nodes

            return nodes

    def switch(self, container, representation):
        self.update(container, representation)


class GpuCacheLoader(api.Loader):
    """Load model Alembic as gpuCache"""

    families = ["model"]
    representations = ["abc"]

    label = "Import Gpu Cache"
    order = -5
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):

        import maya.cmds as cmds
        import avalon.maya.lib as lib
        from avalon.maya.pipeline import containerise

        asset = context['asset']['name']
        namespace = namespace or lib.unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )

        cmds.loadPlugin("gpuCache", quiet=True)

        # Root group
        label = "{}:{}".format(namespace, name)
        root = cmds.group(name=label, empty=True)

        presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
        colors = presets['plugins']['maya']['load']['colors']
        c = colors.get('model')
        if c is not None:
            cmds.setAttr(root + ".useOutlinerColor", 1)
            cmds.setAttr(root + ".outlinerColor",
                         c[0], c[1], c[2])

        # Create transform with shape
        transform_name = label + "_GPU"
        transform = cmds.createNode("transform", name=transform_name,
                                    parent=root)
        cache = cmds.createNode("gpuCache",
                                parent=transform,
                                name="{0}Shape".format(transform_name))

        # Set the cache filepath
        cmds.setAttr(cache + '.cacheFileName', self.fname, type="string")
        cmds.setAttr(cache + '.cacheGeomPath', "|", type="string")    # root

        # Lock parenting of the transform and cache
        cmds.lockNode([transform, cache], lock=True)

        nodes = [root, transform, cache]
        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def update(self, container, representation):

        import maya.cmds as cmds

        path = api.get_representation_path(representation)

        # Update the cache
        members = cmds.sets(container['objectName'], query=True)
        caches = cmds.ls(members, type="gpuCache", long=True)

        assert len(caches) == 1, "This is a bug"

        for cache in caches:
            cmds.setAttr(cache + ".cacheFileName", path, type="string")

        cmds.setAttr(container["objectName"] + ".representation",
                     str(representation["_id"]),
                     type="string")

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        import maya.cmds as cmds
        members = cmds.sets(container['objectName'], query=True)
        cmds.lockNode(members, lock=False)
        cmds.delete([container['objectName']] + members)

        # Clean up the namespace
        try:
            cmds.namespace(removeNamespace=container['namespace'],
                           deleteNamespaceContent=True)
        except RuntimeError:
            pass


# class AbcModelLoader(pype.maya.plugin.ReferenceLoader):
#     """Specific loader of Alembic for the studio.animation family"""
#
#     families = ["model"]
#     representations = ["abc"]
#     tool_names = ["loader"]
#
#     label = "Reference Model"
#     order = -10
#     icon = "code-fork"
#     color = "orange"
#
#     def process_reference(self, context, name, namespace, data):
#
#         import maya.cmds as cmds
#
#         groupName = "{}:{}".format(namespace, name)
#         cmds.loadPlugin("AbcImport.mll", quiet=True)
#         nodes = cmds.file(self.fname,
#                           namespace=namespace,
#                           sharedReferenceFile=False,
#                           groupReference=True,
#                           groupName="{}:{}".format(namespace, name),
#                           reference=True,
#                           returnNewNodes=True)
#
#         namespace = cmds.referenceQuery(nodes[0], namespace=True)
#
#         nodes.pop(0)
#         roots = set()
#         for node in nodes:
#             try:
#                 roots.add(cmds.ls(node, long=True)[0].split('|')[2])
#             except:
#                 pass
#         cmds.parent(roots, world=True)
#         cmds.makeIdentity(groupName, apply=False, rotate=True,
#                           translate=True, scale=True)
#         cmds.parent(roots, groupName)
#
#         nodes.append(groupName)
#
#         presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
#         colors = presets['plugins']['maya']['load']['colors']
#         c = colors.get('model')
#         if c is not None:
#             cmds.setAttr(groupName + ".useOutlinerColor", 1)
#             cmds.setAttr(groupName + ".outlinerColor",
#                          c[0], c[1], c[2])
#
#         self[:] = nodes
#
#         return nodes
#
#     def switch(self, container, representation):
#         self.update(container, representation)
