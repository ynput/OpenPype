import os
import c4d
import openpype.api
from openpype.hosts.cinema4d.api import lib, export_abc


class ExtractCameraAlembic(openpype.api.Extractor):
    """Extract a Camera as Alembic.

    The cameras gets baked to world space by default. Only when the instance's
    `bakeToWorldSpace` is set to False it will include its full hierarchy.

    """

    label = "Camera (Alembic)"
    hosts = ["cinema4d"]
    families = ["camera"]
    bake_attributes = []

    def process(self, instance):
        doc = c4d.documents.GetActiveDocument()
        # Collect the start and end including handles
        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]

        step = instance.data.get("step", 1)
        bake_to_worldspace = instance.data("bakeToWorldSpace", True)

        # get cameras
        members = instance.data['setMembers']
        members = [lib.ObjectPath(x) for x in members]
        cameras = lib.ls(members, exact_type=c4d.CameraObject)


        camera = cameras[0]

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.abc".format(instance.name)
        path = os.path.join(dir_path, filename)

        # Perform alembic extraction

        with lib.maintained_selection():
            first = True
            for camera in cameras:
                if first:
                    flag = c4d.SELECTION_NEW
                    first = False
                else:
                    flag = c4d.SELECTION_ADD
                doc.SetSelection(camera.obj, flag)
            # Enforce forward slashes for AbcExport because we're
            # embedding it into a job string
            path = path.replace("\\", "/")

            settings = {
                "start": int(start),
                "end":int(end),
                "step":int(step),
                "selection":True
                }

            if bake_to_worldspace:
                settings["global"] = True

            export_abc(path, settings, doc)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'abc',
            'ext': 'abc',
            'files': filename,
            "stagingDir": dir_path,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '{0}' to: {1}".format(
            instance.name, path))
