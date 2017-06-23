import pyblish.api
import colorbleed.api
from maya import cmds


class ValidateNamespaceEmpty(pyblish.api.ContextPlugin):
    """Validate there are no empty namespaces in the scene.

    This is a scene wide validation that filters out "UI" and "shared"
    namespaces that exist by default in Maya and are mostly hidden.
    
    A namespace that has other namespaces in it is *not* considered empty.
    Only those that have no children namespaces or nodes is considered empty.

    """

    order = colorbleed.api.ValidateSceneOrder
    hosts = ["maya"]
    families = ["colorbleed.model"]
    label = "No Empty Namespaces"

    def process(self, context):
        """Process the Context"""
        all_namespaces = cmds.namespaceInfo(":",
                                            listOnlyNamespaces=True,
                                            recurse=True)
        non_internal_namespaces = [ns for ns in all_namespaces
                                   if ns not in ["UI", "shared"]]

        invalid = []
        for namespace in non_internal_namespaces:
            namespace_content = cmds.namespaceInfo(namespace,
                                                   listNamespace=True,
                                                   recurse=True)
            if not namespace_content:
                invalid.append(namespace)

        assert not invalid, (
            "Empty namespaces found: {0}".format(invalid))
