import re
import json

from openpype.client import (
    get_representation_by_id,
    get_representations
)
from openpype.pipeline import (
    InventoryAction,
    get_representation_context,
    get_current_project_name,
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
        from maya import cmds  # noqa: F401

        project_name = get_current_project_name()
        for container in containers:
            con_name = container["objectName"]
            nodes = []
            for n in cmds.sets(con_name, query=True, nodesOnly=True) or []:
                if cmds.nodeType(n) == "reference":
                    nodes += cmds.referenceQuery(n, nodes=True)
                else:
                    nodes.append(n)

            repr_doc = get_representation_by_id(
                project_name, container["representation"], fields=["parent"]
            )
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

        from maya import cmds  # noqa: F401

        project_name = get_current_project_name()
        repre_docs = get_representations(
            project_name, version_ids=[version_id], fields=["_id", "name"]
        )
        # Get representations of shader file and relationships
        json_repre = None
        look_repres = []
        scene_type_regex = re.compile(self.scene_type_regex)
        for repre_doc in repre_docs:
            repre_name = repre_doc["name"]
            if repre_name == self.look_data_type:
                json_repre = repre_doc
                continue

            if scene_type_regex.fullmatch(repre_name):
                look_repres.append(repre_doc)

        look_repre = look_repres[0] if look_repres else None
        # QUESTION shouldn't be json representation validated too?
        if not look_repre:
            print("No model render sets for this model version..")
            return

        context = get_representation_context(look_repre["_id"])
        maya_file = self.filepath_from_context(context)

        context = get_representation_context(json_repre["_id"])
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
