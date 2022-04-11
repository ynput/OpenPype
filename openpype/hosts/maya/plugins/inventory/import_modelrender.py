import json
from avalon import io
from bson.objectid import ObjectId
from openpype.pipeline import (
    InventoryAction,
    get_representation_context,
)
from openpype.hosts.maya.api.lib import (
    maintained_selection,
    apply_shaders
)


class ImportModelRender(InventoryAction):

    label = "Import Model Render Sets"
    icon = "industry"
    color = "#55DDAA"

    scene_type_regex = "meta.render.m[ab]"
    look_data_type = "meta.render.json"

    @staticmethod
    def is_compatible(container):
        return (
            container.get("loader") == "ReferenceLoader"
            and container.get("name", "").startswith("model")
        )

    def process(self, containers):
        from maya import cmds

        for container in containers:
            con_name = container["objectName"]
            nodes = []
            for n in cmds.sets(con_name, query=True, nodesOnly=True) or []:
                if cmds.nodeType(n) == "reference":
                    nodes += cmds.referenceQuery(n, nodes=True)
                else:
                    nodes.append(n)

            repr_doc = io.find_one({
                "_id": ObjectId(container["representation"]),
            })
            version_id = repr_doc["parent"]

            print("Importing render sets for model %r" % con_name)
            self.assign_model_render_by_version(nodes, version_id)

    def assign_model_render_by_version(self, nodes, version_id):
        """Assign nodes a specific published model render data version by id.

        This assumes the nodes correspond with the asset.

        Args:
            nodes(list): nodes to assign render data to
            version_id (bson.ObjectId): database id of the version of model

        Returns:
            None
        """

        from maya import cmds

        # Get representations of shader file and relationships
        look_repr = io.find_one({
            "type": "representation",
            "parent": version_id,
            "name": {"$regex": self.scene_type_regex},
        })
        if not look_repr:
            print("No model render sets for this model version..")
            return

        json_repr = io.find_one({
            "type": "representation",
            "parent": version_id,
            "name": self.look_data_type,
        })

        context = get_representation_context(look_repr["_id"])
        maya_file = self.filepath_from_context(context)

        context = get_representation_context(json_repr["_id"])
        json_file = self.filepath_from_context(context)

        # Import the look file
        with maintained_selection():
            shader_nodes = cmds.file(maya_file,
                                     i=True,  # import
                                     returnNewNodes=True)
            # imprint context data

        # Load relationships
        shader_relation = json_file
        with open(shader_relation, "r") as f:
            relationships = json.load(f)

        # Assign relationships
        apply_shaders(relationships, shader_nodes, nodes)
