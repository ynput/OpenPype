from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.pipeline.load import LoadError
from openpype.hosts.substancepainter.api.pipeline import (
    imprint_container,
    set_container_metadata,
    remove_container_metadata
)
from openpype.hosts.substancepainter.api.lib import prompt_new_file_with_mesh

import substance_painter.project
import qargparse


class SubstanceLoadProjectMesh(load.LoaderPlugin):
    """Load mesh for project"""

    families = ["*"]
    representations = ["abc", "fbx", "obj", "gltf"]

    label = "Load mesh"
    order = -10
    icon = "code-fork"
    color = "orange"

    options = [
        qargparse.Boolean(
            "preserve_strokes",
            default=True,
            help="Preserve strokes positions on mesh.\n"
                 "(only relevant when loading into existing project)"
        ),
        qargparse.Boolean(
            "import_cameras",
            default=True,
            help="Import cameras from the mesh file."
        )
    ]

    def load(self, context, name, namespace, data):

        # Get user inputs
        import_cameras = data.get("import_cameras", True)
        preserve_strokes = data.get("preserve_strokes", True)
        sp_settings = substance_painter.project.Settings(
            import_cameras=import_cameras
        )
        if not substance_painter.project.is_open():
            # Allow to 'initialize' a new project
            path = self.filepath_from_context(context)
            # TODO: improve the prompt dialog function to not
            # only works for simple polygon scene
            result = prompt_new_file_with_mesh(mesh_filepath=path)
            if not result:
                self.log.info("User cancelled new project prompt."
                              "Creating new project directly from"
                              " Substance Painter API Instead.")
                settings = substance_painter.project.create(
                    mesh_file_path=path, settings=sp_settings
                )

        else:
            # Reload the mesh
            settings = substance_painter.project.MeshReloadingSettings(
                import_cameras=import_cameras,
                preserve_strokes=preserve_strokes
            )

            def on_mesh_reload(status: substance_painter.project.ReloadMeshStatus):  # noqa
                if status == substance_painter.project.ReloadMeshStatus.SUCCESS:  # noqa
                    self.log.info("Reload succeeded")
                else:
                    raise LoadError("Reload of mesh failed")

            path = self.filepath_from_context(context)
            substance_painter.project.reload_mesh(path,
                                                  settings,
                                                  on_mesh_reload)

        # Store container
        container = {}
        project_mesh_object_name = "_ProjectMesh_"
        imprint_container(container,
                          name=project_mesh_object_name,
                          namespace=project_mesh_object_name,
                          context=context,
                          loader=self)

        # We want store some options for updating to keep consistent behavior
        # from the user's original choice. We don't store 'preserve_strokes'
        # as we always preserve strokes on updates.
        container["options"] = {
            "import_cameras": import_cameras,
        }

        set_container_metadata(project_mesh_object_name, container)

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):

        path = get_representation_path(representation)

        # Reload the mesh
        container_options = container.get("options", {})
        settings = substance_painter.project.MeshReloadingSettings(
            import_cameras=container_options.get("import_cameras", True),
            preserve_strokes=True
        )

        def on_mesh_reload(status: substance_painter.project.ReloadMeshStatus):
            if status == substance_painter.project.ReloadMeshStatus.SUCCESS:
                self.log.info("Reload succeeded")
            else:
                raise LoadError("Reload of mesh failed")

        substance_painter.project.reload_mesh(path, settings, on_mesh_reload)

        # Update container representation
        object_name = container["objectName"]
        update_data = {"representation": str(representation["_id"])}
        set_container_metadata(object_name, update_data, update=True)

    def remove(self, container):

        # Remove OpenPype related settings about what model was loaded
        # or close the project?
        # TODO: This is likely best 'hidden' away to the user because
        #       this will leave the project's mesh unmanaged.
        remove_container_metadata(container["objectName"])
