import json

from bson.objectid import ObjectId

import nuke
import nukescripts

from avalon import api, io
from avalon.nuke import containerise, update_container


class ProjectionLoader(api.Loader):
    """
    This will load camera, pointcache and image to build a projection setup.
    """

    families = ["projection"]
    representations = ["json"]

    label = "Load Projection"
    icon = "camera"
    color = "orange"
    node_color = "0x3469ffff"
    node_padding = 200

    def node_version_color(self, version, node):
        """ Coloring a node by correct color by actual version
        """
        # get all versions in list
        versions = io.find({
            "type": "version",
            "parent": version["parent"]
        }).distinct('name')

        max_version = max(versions)

        # change color of node
        if version.get("name") not in [max_version]:
            node["tile_color"].setValue(int("0xd88467ff", 16))
        else:
            node["tile_color"].setValue(int(self.node_color, 16))

    def setup_nodes(self, json_path, context, control_node=None):
        json_data = None
        with open(json_path, "r") as f:
            json_data = json.loads(f.read())

        # Collect loaders from registry
        camera_loader = None
        pointcache_loader = None
        image_loader = None
        for loader in api.last_discovered_plugins[api.Loader.__name__]:
            if loader.__name__ == "AlembicCameraLoader":
                camera_loader = loader
            if loader.__name__ == "AlembicPointcacheLoader":
                pointcache_loader = loader
            if loader.__name__ == "LoadImage":
                image_loader = loader

        # Generate contexts for loaders.
        version = io.find_one({"_id": ObjectId(json_data["cameraVersionId"])})
        subset = io.find_one({"_id": version["parent"]})
        representation = io.find_one(
            {"type": "representation", "parent": version["_id"], "name": "abc"}
        )
        camera_context = {
            "project": context["project"],
            "asset": context["asset"],
            "subset": subset,
            "version": version,
            "representation": representation
        }

        version = io.find_one(
            {"_id": ObjectId(json_data["pointcacheVersionId"])}
        )
        subset = io.find_one({"_id": version["parent"]})
        representation = io.find_one(
            {
                "type": "representation",
                "parent": version["_id"],
                "name": "abc"
            }
        )
        pointcache_context = {
            "project": context["project"],
            "asset": context["asset"],
            "subset": subset,
            "version": version,
            "representation": representation
        }

        # Process assignments data.
        rgb_attributes = ["outColor", "color"]
        alpha_attributes = ["outTransparency"]
        materials_data = {}
        for data in json_data["assignments"]:
            material_data = {}
            try:
                material_data = materials_data[data["material"]]
            except KeyError:
                pass

            if data["attribute"] in rgb_attributes:
                material_data["rgb"] = data["versionId"]

            if data["attribute"] in alpha_attributes:
                material_data["alpha"] = data["versionId"]

            try:
                shapes = material_data["shapes"]
            except KeyError:
                shapes = []
            if data["shape"] not in shapes:
                shapes.append(data["shape"])
            material_data["shapes"] = shapes

            materials_data[data["material"]] = material_data

        # Setup data pipes.
        pointcache_nodes = []
        projection_nodes = []
        invert_alpha_nodes = []
        last_node = None
        for material, data in materials_data.items():
            all_nodes = []

            # Load rgb image.
            version = io.find_one(
                {"_id": ObjectId(data["rgb"])}
            )
            subset = io.find_one({"_id": version["parent"]})
            representation = io.find_one(
                {
                    "type": "representation",
                    "parent": version["_id"],
                    "name": {"$in": image_loader.representations}
                }
            )
            image_context = {
                "project": context["project"],
                "asset": context["asset"],
                "subset": subset,
                "version": version,
                "representation": representation
            }
            image_node = image_loader(image_context).load(
                image_context, subset["name"], None, {}
            )
            all_nodes.append(image_node)

            # Load alpha image.
            alpha_node = None
            if "alpha" in data:
                version = io.find_one(
                    {"_id": ObjectId(data["alpha"])}
                )
                subset = io.find_one({"_id": version["parent"]})
                representation = io.find_one(
                    {
                        "type": "representation",
                        "parent": version["_id"],
                        "name": {"$in": image_loader.representations}
                    }
                )
                image_context = {
                    "project": context["project"],
                    "asset": context["asset"],
                    "subset": subset,
                    "version": version,
                    "representation": representation
                }
                alpha_node = image_loader(image_context).load(
                    image_context, subset["name"], None, {}
                )
                all_nodes.append(alpha_node)

            # Load pointcache.
            pointcache_node = pointcache_loader(pointcache_context).load(
                pointcache_context, subset["name"], None, {}
            )
            scene_view = pointcache_node["scene_view"]
            items = []
            for item in scene_view.getAllItems():
                for shape_name in data["shapes"]:
                    if item.endswith(shape_name):
                        items.append(item)
            scene_view.setImportedItems(items)
            scene_view.setSelectedItems(items)

            pointcache_nodes.append(pointcache_node)
            all_nodes.append(pointcache_node)

            # Load camera.
            camera_node = camera_loader(camera_context).load(
                camera_context, subset["name"], None, {}
            )
            all_nodes.append(camera_node)

            # Projection node.
            projection_node = nuke.createNode("Project3D2")
            projection_nodes.append(projection_node)
            all_nodes.append(projection_node)

            # Setup nodes.
            if last_node:
                image_node.setXYpos(
                    last_node.xpos() + (2 * self.node_padding), 0
                )
            else:
                image_node.setXYpos(0, 0)
            last_node = image_node

            if alpha_node:
                shuffle_copy_node = nuke.createNode("ShuffleCopy")
                shuffle_copy_node.setInput(0, image_node)
                shuffle_copy_node.setInput(1, alpha_node)
                shuffle_copy_node["alpha"].setValue("red")
                shuffle_copy_node.setXYpos(
                    last_node.xpos(), last_node.ypos() + self.node_padding
                )

                alpha_node.setXYpos(
                    shuffle_copy_node.xpos() - self.node_padding,
                    shuffle_copy_node.ypos()
                )

                invert_alpha_node = nuke.createNode("Invert")
                invert_alpha_node.setInput(0, shuffle_copy_node)
                invert_alpha_node["channels"].setValue("alpha")
                invert_alpha_node.autoplace()
                invert_alpha_nodes.append(invert_alpha_node)

                premult_node = nuke.createNode("Premult")
                premult_node.setInput(0, invert_alpha_node)
                premult_node.autoplace()

                last_node = premult_node
                all_nodes.extend(
                    [shuffle_copy_node, invert_alpha_node, premult_node]
                )

            projection_node.setInput(0, last_node)
            projection_node.setInput(1, camera_node)
            projection_node.setXYpos(
                last_node.xpos(), last_node.ypos() + self.node_padding
            )
            last_node = projection_node

            camera_node.setXYpos(
                projection_node.xpos() - self.node_padding,
                projection_node.ypos()
            )

            pointcache_node.setInput(0, last_node)
            pointcache_node.autoplace()
            last_node = pointcache_node

            for node in nuke.allNodes():
                if node in all_nodes:
                    node["selected"].setValue(True)
                else:
                    node["selected"].setValue(False)
            backdrop = nukescripts.autoBackdrop()
            backdrop.setName(material)
            backdrop["label"].setValue(material)

        # Scene node.
        scene_node = nuke.createNode("Scene")
        for count, node in enumerate(pointcache_nodes):
            scene_node.setInput(count, node)

        scene_node.setXYpos(
            pointcache_nodes[0].xpos(), pointcache_nodes[0].ypos() + 300
        )

        # Output node.
        output_node = nuke.createNode("Output")
        output_node.setInput(0, scene_node)

        # Control node.
        valid_knobs = ["crop", "project_on", "occlusion_mode"]
        if not control_node:
            control_node = nuke.createNode(
                "Project3D2", "name control"
            )

            control_node.setXYpos(
                scene_node.xpos() - 100, scene_node.ypos()
            )
            code = """
this_node = nuke.thisNode()
this_knob = nuke.thisKnob()
valid_knobs = {}
for node in nuke.allNodes(filter="Project3D2"):
    if node == this_node:
        continue

    if this_knob.name() not in valid_knobs:
        continue

    node[this_knob.name()].setValue(this_knob.value())
            """.format(valid_knobs)

            control_node["knobChanged"].setValue(code)

            knob = nuke.Boolean_Knob("invert_alpha", "Invert Alpha")
            control_node.addKnob(knob)

        for node in projection_nodes:
            for knob_name in valid_knobs:
                node[knob_name].setValue(control_node[knob_name].value())

        for node in invert_alpha_nodes:
            node["disable"].setExpression(
                "!{}.invert_alpha".format(control_node.name())
            )

        return control_node

    def load(self, context, name, namespace, data):
        # Setup group.
        # Adding "1" to the end will encourage Nuke to increment this number
        # for multiple instances of the pointcache.
        object_name = "{}_{}_1".format(name, context["asset"]["name"])
        group_node = nuke.createNode("Group", "name {}".format(object_name))

        self.node_version_color(context["version"], group_node)

        # Execute inside group.
        control_node = None
        with group_node:
            control_node = self.setup_nodes(self.fname, context)
        assert control_node is not None, "Setting up nodes went wrong."

        containerise(
            node=group_node,
            name=name,
            namespace=context["asset"]["name"],
            context=context,
            loader=self.__class__.__name__,
            data={"objectName": group_node.name()}
        )

        group_node.addKnob(nuke.Text_Knob(""))

        knob_names = ["crop", "project_on", "occlusion_mode", "invert_alpha"]
        for knob_name in knob_names:
            knob = control_node[knob_name]
            label = knob.label()
            if not knob.label():
                label = knob.name()
            link_knob = nuke.Link_Knob(knob.name(), label)
            link_knob.setLink("{}.{}".format(
                control_node.name(), knob.name())
            )
            group_node.addKnob(link_knob)

        return group_node

    def update(self, container, representation):
        version = io.find_one({"_id": representation["parent"]})
        subset = io.find_one({"_id": version["parent"]})
        asset = io.find_one({"_id": subset["parent"]})
        project = io.find_one({"_id": asset["parent"]})
        context = {
            "representation": representation,
            "version": version,
            "subset": subset,
            "asset": asset,
            "project": project
        }
        json_path = api.get_representation_path(representation)

        # Execute inside group.
        group_node = nuke.toNode(container["objectName"])
        with group_node:
            control_node = None
            for node in nuke.allNodes():
                if node.name() == "control":
                    control_node = node
                    continue
                nuke.delete(node)

            self.setup_nodes(json_path, context, control_node=control_node)

        update_container(
            group_node, {"representation": str(representation["_id"])}
        )
        self.node_version_color(context["version"], group_node)

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from avalon.nuke import viewer_update_and_undo_stop
        node = nuke.toNode(container["objectName"])
        with viewer_update_and_undo_stop():
            nuke.delete(node)
