import tempfile
import zipfile
import os
import shutil
import uuid

from avalon import api, harmony
import pype.lib

load_container = """load_container = function(args) {  
    var doc = $.scn;
    var template_path = args[0];
    var asset_name = args[1];
    var subset = args[2];
    var group_id = args[3];
    
    node_view_widget = $.app.getWidgetByName('Node View');
   
    if (!node_view_widget){
        $.alert("You must have a Node View open!, "No Node View!" )

    node_view_widget.setFocus();
 
    const node_view = view.currentView();
    
    const current_group = doc.$node(view.group(node_view));
  
    // Get a unique iterative name for the container group
    var num = 0;
    var container_group_name = "";
    do {container_group_name = asset_name + "_" + (num++) + "_" + subset;
    } while (current_group.getNodeByName(container_group_name) != null);
    
    // import the template
    var tpl_nodes = current_group.importTemplate(template_path);
    MessageLog.trace(tpl_nodes)
    // Create the container group  
    var group_node = current_group.addGroup(
        container_group_name, false, false, tpl_nodes);
    
    // Add uuid to attribute of the container group
    node.createDynamicAttr(group_node, "STRING", "uuid", "uuid", false)
    node.setTextAttr(group_node, "uuid", 1.0, group_id)
    
    return String(group_node);
};
load_container

"""

replace_node = """
function replace_node(dst_node_path, src_node_path, rename_src, clone_src, link_columns) {

    var doc = $.scn
    var src_node = doc.$node(src_node_path)
    var dst_node = doc.$node(dst_node_path)
    const dst_node_name = dst_node.name
    var replacement_node = src_node
    const dst_group = dst_node.group

    $.beginUndo()

    if (clone_src) {
        var replacement_node = doc.$node(
            Y.nodeTools.copy_paste_node(src_node_path, dst_node.name + "_CLONE", dst_node.group.path))
    }
    else {
        if (replacement_node.group.path != src_node.group.path) {
            replacement_node.moveToGroup(dst_group)
        }
    }

    var in_links = dst_node.getInLinks()

    for (l in in_links) {
        var link = in_links[l]

        in_port = Number(link.inPort)
        out_port = Number(link.outPort)
        out_node = link.outNode
        success = replacement_node.linkInNode(out_node, in_port, out_port)

        if (success) {
            log("Successfully connected " + out_node + " : " + out_port + " -> " + replacement_node + " : " + in_port)
        } else {
            log("Failed to connect " + out_node + " : " + out_port + " -> " + replacement_node + " : " + in_port)
        }
    }

    var out_links = dst_node.getOutLinks()

    for (l in out_links) {
        var link = out_links[l]
        in_port = Number(link.inPort)
        out_port = Number(link.outPort)
        in_node = link.inNode
        // first we must disconnect the port from the node being replaced to this links inNode port
        in_node.unlinkInPort(in_port)

        success = replacement_node.linkOutNode(in_node, out_port, in_port)

        if (success) {
            log("Successfully connected " + in_node + " : " + in_port + " <- " + replacement_node + " : " + out_port)
        } else {
            if (in_node.type == "MultiLayerWrite") {
                log("Attempting standard api to connect the nodes...")
                success = node.link(replacement_node, out_port, in_node, in_port, node.numberOfInputPorts(in_node) + 1)
                if (success) {
                    log("Successfully connected " + in_node + " : " + in_port + " <- " + replacement_node + " : " + out_port)
                }
            }
        }
        if (!success) {
            log("Failed to connect " + in_node + " : " + in_port + " <- " + replacement_node + " : " + out_port)
            return false
        }
    }"""

class LoadTemplateLoader(api.Loader):
    """Load Harmony template as container."""

    families = ["template, "workfile"]
    representations = ["*"]
    label = "Load Template"
    icon = "gift"

    def load(self, context, name=None, namespace=None, data=None):
        # Load template.
        temp_dir = tempfile.mkdtemp()
        zip_file = api.get_representation_path(context["representation"])
        template_path = os.path.join(temp_dir, "temp.tpl")
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(template_path)

        group_id = "{}".format(uuid.uuid4())

        container_group = harmony.send(
            {
                "function": load_container,
                "args": [template_path,
                         context["asset"]["name"],
                         context["subset"]["name"],
                         group_id]
            }
        )["result"]

        shutil.rmtree(temp_dir)

        # We must validate the group_node
        return harmony.containerise(
            name,
            namespace,
            container_group,
            context,
            self.__class__.__name__
        )

    def update(self, container, representation):

        node_name = container["name"]
        node = harmony.find_node_by_name(node_name, "GROUP")

        func = """function func(args){
                    var red_color = new ColorRGBA(255, 0, 0, 255);
                    var green_color = new ColorRGBA(0, 255, 0, 255);
                    
                    if (args[1] == "red"){
                        node.setColor(args[0], red_color);
                    }
                    if (args[1] == "green"){
                        node.setColor(args[0], green_color);
                    }
                    
                    // Ask user if they want to also update columns and 
                    // linked attributes here
                    var update_and_replace($.confirm(
                        "Would you like to update in place and reconnect all \n"
                        "ins/outs, attributes, and columns?",
                        "Update & Replace?\n"
                        "If you choose No, the version will only be loaded.",
                        "Yes",
                        "No")
                    return update_and_replace
                }
                func
                """
        update_and_replace = False
        if pype.lib.is_latest(representation):
            update_and_replace = harmony.send(
                {"function": func, "args": [node, "green"]}
            )["result"]
        else:
            update_and_replace = harmony.send(
                {"function": func, "args": [node, "green"]}
            )["result"]

        self.load(container["context"],
                  container["name"],
                  None,
                  container["data"]
                  )

        if update_and_replace:
            new_container = harmony.send(
                {"function": func, "args": [node, "green"]}
            )["result"]

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

class LoadWorkfileLoader(LoadTemplateLoader):
    """Load scenes and workfiles."""

    families = ["template, "workfile"]
    representations = ["zip"]
    label = "Load Template"
