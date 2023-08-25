import os

from openpype.hosts.max.api import lib
from openpype.hosts.max.api.lib import (
    unique_namespace,
    get_namespace,
    maintained_selection,
    object_transform_set
)
from openpype.hosts.max.api.lib import maintained_selection
from openpype.hosts.max.api.pipeline import (
    containerise,
    import_custom_attribute_data,
    update_custom_attribute_data
)
from openpype.pipeline import get_representation_path, load


class ObjLoader(load.LoaderPlugin):
    """Obj Loader."""

    families = ["model"]
    representations = ["obj"]
    order = -9
    icon = "code-fork"
    color = "white"
    postfix = "param"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        filepath = os.path.normpath(self.filepath_from_context(context))
        self.log.debug("Executing command to import..")

        rt.Execute(f'importFile @"{filepath}" #noPrompt using:ObjImp')

        namespace = unique_namespace(
            name + "_",
            suffix="_",
        )
        # create "missing" container for obj import
        container = rt.Container(name=f"{namespace}:{name}_{self.postfix}")
        selections = rt.GetCurrentSelection()
        import_custom_attribute_data(container, selections)
        # get current selection
        for selection in selections:
            selection.Parent = container
            selection.name = f"{namespace}:{selection.name}"
        return containerise(
            name, [container], context,
            namespace, loader=self.__class__.__name__)

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node_name = container["instance_node"]
        node = rt.getNodeByName(node_name)
        namespace, name = get_namespace(node_name)
        sub_node_name = f"{namespace}:{name}_{self.postfix}"
        inst_container = rt.getNodeByName(sub_node_name)
        rt.Select(inst_container.Children)
        transform_data = object_transform_set(inst_container.Children)
        for prev_obj in rt.selection:
            if rt.isValidNode(prev_obj):
                rt.Delete(prev_obj)

        rt.Execute(f'importFile @"{path}" #noPrompt using:ObjImp')
        # get current selection
        selections = rt.GetCurrentSelection()
        update_custom_attribute_data(inst_container, selections)
        for selection in selections:
            selection.Parent = inst_container
            selection.name = f"{namespace}:{selection.name}"
            selection.pos = transform_data[
                f"{selection.name}.transform"]
            selection.scale = transform_data[
                f"{selection.name}.scale"]
        with maintained_selection():
            rt.Select(node)

        lib.imprint(node_name, {
            "representation": str(representation["_id"])
        })

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)
