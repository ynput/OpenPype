import os
from openpype.pipeline import load, get_representation_path
from openpype.hosts.max.api.pipeline import (
    containerise,
    import_custom_attribute_data,
    update_custom_attribute_data
)
from openpype.hosts.max.api import lib
from openpype.hosts.max.api.lib import (
    maintained_selection, unique_namespace
)


class ModelAbcLoader(load.LoaderPlugin):
    """Loading model with the Alembic loader."""

    families = ["model"]
    label = "Load Model(Alembic)"
    representations = ["abc"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):
        from pymxs import runtime as rt

        file_path = os.path.normpath(self.filepath_from_context(context))

        abc_before = {
            c
            for c in rt.rootNode.Children
            if rt.classOf(c) == rt.AlembicContainer
        }

        rt.AlembicImport.ImportToRoot = False
        rt.AlembicImport.CustomAttributes = True
        rt.AlembicImport.UVs = True
        rt.AlembicImport.VertexColors = True
        rt.importFile(file_path, rt.name("noPrompt"), using=rt.AlembicImport)

        abc_after = {
            c
            for c in rt.rootNode.Children
            if rt.classOf(c) == rt.AlembicContainer
        }

        # This should yield new AlembicContainer node
        abc_containers = abc_after.difference(abc_before)

        if len(abc_containers) != 1:
            self.log.error("Something failed when loading.")

        abc_container = abc_containers.pop()
        import_custom_attribute_data(
            abc_container, abc_container.Children)

        namespace = unique_namespace(
            name + "_",
            suffix="_",
        )

        return containerise(
            name, [abc_container], context,
            namespace, loader=self.__class__.__name__
        )

    def update(self, container, representation):
        from pymxs import runtime as rt

        path = get_representation_path(representation)
        node = rt.GetNodeByName(container["instance_node"])

        with maintained_selection():
            rt.Select(node.Children)

            for alembic in rt.Selection:
                abc = rt.GetNodeByName(alembic.name)
                update_custom_attribute_data(abc, abc.Children)
                rt.Select(abc.Children)
                for abc_con in abc.Children:
                    abc_con.source = path
                    rt.Select(abc_con.Children)
                    for abc_obj in abc_con.Children:
                        abc_obj.source = path

        lib.imprint(
            container["instance_node"],
            {"representation": str(representation["_id"])},
        )

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from pymxs import runtime as rt

        node = rt.GetNodeByName(container["instance_node"])
        rt.Delete(node)

    @staticmethod
    def get_container_children(parent, type_name):
        from pymxs import runtime as rt

        def list_children(node):
            children = []
            for c in node.Children:
                children.append(c)
                children += list_children(c)
            return children

        filtered = []
        for child in list_children(parent):
            class_type = str(rt.ClassOf(child.baseObject))
            if class_type == type_name:
                filtered.append(child)

        return filtered
