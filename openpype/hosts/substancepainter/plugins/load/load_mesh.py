from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.substancepainter.api.pipeline import imprint_container

import substance_painter.project
import qargparse


def set_container(key, container):
    metadata = substance_painter.project.Metadata("OpenPype")
    containers = metadata.get("containers") or {}
    containers[key] = container
    metadata.set("containers", containers)


def remove_container(key):
    metadata = substance_painter.project.Metadata("OpenPype")
    containers = metadata.get("containers")
    if containers:
        containers.pop(key, None)
        metadata.set("containers", containers)


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

    container_key = "ProjectMesh"

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

        else:
            # Reload the mesh
            settings = substance_painter.project.MeshReloadingSettings(
                import_cameras=data.get("import_cameras", True),
                preserve_strokes=data.get("preserve_strokes", True)
            )

            def on_mesh_reload(status: substance_painter.project.ReloadMeshStatus):  # noqa
                if status == substance_painter.project.ReloadMeshStatus.SUCCESS:  # noqa
                    print("Reload succeeded")
                else:
                    raise RuntimeError("Reload of mesh failed")

            path = self.fname
            substance_painter.project.reload_mesh(path,
                                                  settings,
                                                  on_mesh_reload)

        # Store container
        container = {}
        imprint_container(container,
                          name=self.container_key,
                          namespace=self.container_key,
                          context=context,
                          loader=self)
        container["options"] = data
        set_container(self.container_key, container)

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):

        path = get_representation_path(representation)

        # Reload the mesh
        # TODO: Re-use settings from first load?
        container_options = container.get("options", {})
        settings = substance_painter.project.MeshReloadingSettings(
            import_cameras=container_options.get("import_cameras", True),
            preserve_strokes=container_options.get("preserve_strokes", True)
        )

        def on_mesh_reload(status: substance_painter.project.ReloadMeshStatus):
            if status == substance_painter.project.ReloadMeshStatus.SUCCESS:
                print("Reload succeeded")
            else:
                raise RuntimeError("Reload of mesh failed")

        substance_painter.project.reload_mesh(path, settings, on_mesh_reload)

        # Update container representation
        container["representation"] = str(representation["_id"])
        set_container(self.container_key, container)

    def remove(self, container):

        # Remove OpenPype related settings about what model was loaded
        # or close the project?
        # TODO: This is likely best 'hidden' away to the user because
        #       this will leave the project's mesh unmanaged.
        remove_container(self.container_key)
