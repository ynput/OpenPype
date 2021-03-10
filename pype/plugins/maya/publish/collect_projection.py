import os
import json

from bson.objectid import ObjectId

import pymel.core as pc

import pyblish.api
from avalon import io


class CollectProjection(pyblish.api.InstancePlugin):
    """Collect The geometry, camera and texture for projection."""

    # Offset to be after instance collection.
    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Projection"
    hosts = ["maya"]
    families = ["projection"]

    def ensure_unique_id(self, id):
        if io.find_one({"_id": id}) is None:
            return id
        else:
            return self.ensure_unique_id(ObjectId())

    def process(self, instance):
        # Collect nodes data.
        material_types = ["lambert", "surfaceShader"]
        cameras = []
        assignments = []
        for node in instance[:]:
            shape = pc.PyNode(node)
            if shape.nodeType() != "mesh":
                shape = pc.PyNode(node).getShape()
            shading_engine = shape.connections(type="shadingEngine")[0]
            material = shading_engine.connections(type=material_types)[0]

            connections = material.connections(
                type="projection", connections=True
            )
            for attribute, projection in connections:
                cameras.append(projection.connections(type="camera")[0])
                file_node = projection.connections(type="file")[0]
                path = file_node.fileTextureName.get()
                assignments.append(
                    {
                        "path": path,
                        "material": material.name(),
                        "shape": shape.name(),
                        "attribute": attribute.name(includeNode=False)
                    }
                )

        # Collect camera instances (Will be validated to a single camera).
        camera_name = cameras[0].getTransform().name()
        camera_instance = instance.context.create_instance(camera_name)
        camera_instance.data.update(instance.data)
        camera_instance.data["name"] = instance.data["name"] + "_camera"
        camera_instance.data["subset"] += "Camera"
        camera_instance.data["family"] = "camera"
        camera_instance.data["families"] = []
        camera_instance.data["setMembers"] = [camera_name]
        camera_instance.data["versionId"] = self.ensure_unique_id(ObjectId())
        camera_instance.data["objectName"] = instance.data["name"]

        # Collect pointcache instance.
        pointcache_instance = instance.context.create_instance(instance[0])
        pointcache_instance[:] = instance[:]
        pointcache_instance.data.update(instance.data)
        pointcache_instance.data["name"] = (
            instance.data["name"] + "_pointcache"
        )
        pointcache_instance.data["subset"] += "Pointcache"
        pointcache_instance.data["family"] = "pointcache"
        pointcache_instance.data["families"] = []
        pointcache_instance.data["versionId"] = self.ensure_unique_id(
            ObjectId()
        )
        pointcache_instance.data["objectName"] = instance.data["name"]

        # Collect image instances.
        version_ids = {}
        paths = []
        for data in assignments:
            if data["path"] in paths:
                continue

            paths.append(data["path"])

            image_instance = instance.context.create_instance(data["path"])
            image_instance.data.update(instance.data)
            name = "{}{}{}".format(
                instance.data["name"],
                data["material"].title(),
                data["attribute"].title()
            )
            image_instance.data["name"] = name
            image_instance.data["label"] = "{} ({})".format(
                name, os.path.basename(data["path"])
            )
            image_instance.data["subsetGroup"] = (
                instance.data["subset"] + "Image"
            )
            image_instance.data["subset"] = name
            image_instance.data["family"] = "image"
            image_instance.data["families"] = []

            if data["path"] not in version_ids:
                version_id = self.ensure_unique_id(ObjectId())
                image_instance.data["versionId"] = version_id
                version_ids[data["path"]] = str(version_id)

            ext = os.path.splitext(data["path"])[1][1:]
            image_instance.data["representations"] = [
                {
                    "name": ext,
                    "ext": ext,
                    "files": os.path.basename(data["path"]),
                    "stagingDir": os.path.dirname(data["path"])
                }
            ]
            self.log.info(image_instance.data["representations"])

        for data in assignments:
            data["versionId"] = version_ids[data["path"]]
            del data["path"]

        # Collect instance data.
        instance.data["jsonData"] = {
            "assignments": assignments,
            "cameraVersionId": str(camera_instance.data["versionId"]),
            "pointcacheVersionId": str(pointcache_instance.data["versionId"])
        }
        self.log.info(
            json.dumps(instance.data["jsonData"], sort_keys=True, indent=4)
        )
        instance.data["cameras"] = list(set(cameras))
