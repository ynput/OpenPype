from avalon import api


class ReferenceLoader(api.Loader):
    """A basic ReferenceLoader for Maya
    
    This will implement the basic behavior for a loader to inherit from that
    will containerize the reference and will implement the `remove` and
    `update` logic.
    
    """
    def load(self,
             context,
             name=None,
             namespace=None,
             data=None):

        from avalon.maya import lib
        from avalon.maya.pipeline import containerise

        asset = context['asset']

        namespace = namespace or lib.unique_namespace(
            asset["name"] + "_",
            prefix="_" if asset["name"][0].isdigit() else "",
            suffix="_",
        )

        self.process_reference(context=context,
                               name=name,
                               namespace=namespace,
                               data=data)

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        if not nodes:
            return

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def process_reference(self, context, name, namespace, data):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def update(self, container, representation):

        import os
        from maya import cmds

        node = container["objectName"]

        path = api.get_representation_path(representation)

        # Assume asset has been referenced
        reference_node = next((node for node in cmds.sets(node, query=True)
                               if cmds.nodeType(node) == "reference"), None)

        file_type = {
            "ma": "mayaAscii",
            "mb": "mayaBinary",
            "abc": "Alembic"
        }.get(representation["name"])

        assert file_type, "Unsupported representation: %s" % representation

        assert os.path.exists(path), "%s does not exist." % path
        cmds.file(path, loadReference=reference_node, type=file_type)

        # Fix PLN-40 for older containers created with Avalon that had the
        # `.verticesOnlySet` set to True.
        if cmds.getAttr(node + ".verticesOnlySet"):
            self.log.info("Setting %s.verticesOnlySet to False", node)
            cmds.setAttr(node + ".verticesOnlySet", False)

        # TODO: Add all new nodes in the reference to the container
        #   Currently new nodes in an updated reference are not added to the
        #   container whereas actually they should be!
        nodes = cmds.referenceQuery(reference_node, nodes=True, dagPath=True)
        cmds.sets(nodes, forceElement=node)

        # Update metadata
        cmds.setAttr(node + ".representation",
                     str(representation["_id"]),
                     type="string")

    def remove(self, container):
        """Remove an existing `container` from Maya scene

        Deprecated; this functionality is replaced by `api.remove()`

        Arguments:
            container (avalon-core:container-1.0): Which container
                to remove from scene.

        """

        from maya import cmds

        node = container["objectName"]

        # Assume asset has been referenced
        reference_node = next((node for node in cmds.sets(node, query=True)
                               if cmds.nodeType(node) == "reference"), None)

        assert reference_node, ("Imported container not supported; "
                                "container must be referenced.")

        self.log.info("Removing '%s' from Maya.." % container["name"])

        namespace = cmds.referenceQuery(reference_node, namespace=True)
        fname = cmds.referenceQuery(reference_node, filename=True)
        cmds.file(fname, removeReference=True)

        try:
            cmds.delete(node)
        except ValueError:
            # Already implicitly deleted by Maya upon removing reference
            pass

        try:
            # If container is not automatically cleaned up by May (issue #118)
            cmds.namespace(removeNamespace=namespace,
                           deleteNamespaceContent=True)
        except RuntimeError:
            pass
