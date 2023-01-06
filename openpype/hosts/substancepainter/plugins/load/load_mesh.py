from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.pipeline import legacy_io

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

        if not substance_painter.project.is_open():
            # Allow to 'initialize' a new project
            # TODO: preferably these settings would come from the actual
            #       new project prompt of Substance (or something that is
            #       visually similar to still allow artist decisions)
            settings = substance_painter.project.Settings(
                default_texture_resolution=4096,
                import_cameras=data.get("import_cameras", True),
            )

            substance_painter.project.create(
                mesh_file_path=self.fname,
                settings=settings
            )
            return

        # Reload the mesh
        settings = substance_painter.project.MeshReloadingSettings(
            import_cameras=data.get("import_cameras", True),
            preserve_strokes=data.get("preserve_strokes", True)
        )

        def on_mesh_reload(status: substance_painter.project.ReloadMeshStatus):
            if status == substance_painter.project.ReloadMeshStatus.SUCCESS:
                print("Reload succeeded")
            else:
                raise RuntimeError("Reload of mesh failed")

        path = self.fname
        substance_painter.project.reload_mesh(path, settings, on_mesh_reload)

        # TODO: Register with the project so host.get_containers() can return
        #       the loaded content in manager

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):

        path = get_representation_path(representation)

        # Reload the mesh
        # TODO: Re-use settings from first load?
        settings = substance_painter.project.MeshReloadingSettings(
            import_cameras=True,
            preserve_strokes=True
        )

        def on_mesh_reload(status: substance_painter.project.ReloadMeshStatus):
            if status == substance_painter.project.ReloadMeshStatus.SUCCESS:
                print("Reload succeeded")
            else:
                raise RuntimeError("Reload of mesh failed")

        substance_painter.project.reload_mesh(path, settings, on_mesh_reload)

    def remove(self, container):

        # Remove OpenPype related settings about what model was loaded
        # or close the project?
        pass
