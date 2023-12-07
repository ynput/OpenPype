from openpype.pipeline import load
from openpype.hosts.gaffer.api import get_root

import Gaffer


class GafferImportScene(load.LoaderPlugin):
    """Import a gaffer scene (unmanaged)"""

    families = ["gafferScene", "workfile"]
    representations = ["gfr"]

    label = "Import Gaffer Scene"
    order = -1
    icon = "code-fork"
    color = "white"

    def load(self, context, name, namespace, data):

        script = get_root()
        path = self.filepath_from_context(context).replace("\\", "/")

        with Gaffer.UndoScope(script):
            new_children = []

            def get_new_children(parent, child):
                """Capture new children from import via `childAddedSignal`"""
                new_children.append(child)

            callback = script.childAddedSignal().connect(  # noqa
                get_new_children, scoped=True
            )
            script.importFile(path, parent=script, continueOnError=True)

            new_nodes = [child for child in new_children
                         if isinstance(child, Gaffer.Node)]

            # Select new nodes
            selection = script.selection()
            selection.clear()
            selection.add(new_nodes)

            del callback
