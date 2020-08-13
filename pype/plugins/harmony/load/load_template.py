import tempfile
import zipfile
import os
import shutil
import clique
import uuid

from avalon import api, harmony
import pype.lib

class ImportTemplateLoader(api.Loader):
    """Load templates."""

    families = ["scene", "workfile"]
    representations = ["*"]
    label = "Load Template"

    def load(self, context, name=None, namespace=None, data=None):
        # Import template.
        temp_dir = tempfile.mkdtemp()
        zip_file = api.get_representation_path(context["representation"])
        template_path = os.path.join(temp_dir, "temp.tpl")
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(template_path)

        func = """function func(args)
        {
            var template_path = args[0];
            var drag_object = copyPaste.pasteTemplateIntoGroup(
                template_path,  group_name, 1
            );
            
            var group_name = args[1];
            
            Action.perform("onActionSelCreateGroup()");
            group_node = selection.selectedNodes()[0];
            node.rename(group_node, group_name);
            
            group_path = group_node.split("/").slice(0, -1).join("/") ;
            group_node = group_path + "/" + group_name;
            
            var group_id = args[2];
            
            node.createDynamicAttr(group_node, "STRING", "uuid", "uuid", false)

            node.setTextAttr(group_node, "uuid", 1.0, group_id)
            return group_node;
        }
        func
        """

        name = "{}_{}".format(context["asset"], context["subset"]["name"])
        group_id = "{}".format(uuid.uuid4())

        group_node = harmony.send(
            {
                "function": func,
                "args": [template_path, name, group_id]
            }
        )["result"]

        shutil.rmtree(temp_dir)

        return harmony.containerise(
            "{}_{}".format(name, group_id),
            namespace,
            group_node,
            context,
            self.__class__.__name__
        )

    def update(self, container, representation):

        node_name = "_".join(container["name"].split("_")[:-1])

        node = harmony.find_node_by_name(node_name, "GROUP")

        func = """function func(args){
                    for( var i =0; i <= args[0].length - 1; ++i)
                    {
                        var red_color = new ColorRGBA(255, 0, 0, 255);
                        var green_color = new ColorRGBA(0, 255, 0, 255);
                        if (args[1] == "red"){
                            node.setColor(args[0], red_color);
                        }
                        if (args[1] == "green"){
                            node.setColor(args[0], green_color);
                        }
                    }
                }
                func
                """

        if pype.lib.is_latest(representation):
            harmony.send({"function": func, "args": [node, "green"]})
        else:
            harmony.send({"function": func, "args": [node, "red"]})


        harmony.imprint(
            node, {"representation": str(representation["_id"])}
        )

    def remove(self, container):
        node = harmony.find_node_by_name(container["name"], "GROUP")

        func = """function deleteNode(_node)
        {
            node.deleteNode(_node, true, true);
        }
        deleteNode
        """
        harmony.send(
            {"function": func, "args": [node]}
        )

    def switch(self, container, representation):
        self.update(container, representation)

class LoadWorkfileLoader(ImportTemplateLoader):
    """Load scenes and workfiles."""

    families = ["scene", "workfile"]
    representations = ["zip"]
    label = "Load Template"
