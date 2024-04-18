from qtpy import QtWidgets, QtCore
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


def _convert(substance_attr):
    """Return Substance Painter Python API Project attribute from string.

    This converts a string like "ProjectWorkflow.Default" to for example
    the Substance Painter Python API equivalent object, like:
        `substance_painter.project.ProjectWorkflow.Default`

    Args:
        substance_attr (str): The `substance_painter.project` attribute,
            for example "ProjectWorkflow.Default"

    Returns:
        Any: Substance Python API object of the project attribute.

    Raises:
        ValueError: If attribute does not exist on the
            `substance_painter.project` python api.
    """
    root = substance_painter.project
    for attr in substance_attr.split("."):
        root = getattr(root, attr, None)
        if root is None:
            raise ValueError(
                "Substance Painter project attribute"
                f" does not exist: {substance_attr}")

    return root


def get_template_by_name(name: str, templates: list[dict]) -> dict:
    return next(
        template for template in templates
        if template["name"] == name
    )


class SubstanceProjectConfigurationWindow(QtWidgets.QDialog):
    """The pop-up dialog allows users to choose material
    duplicate options for importing Max objects when updating
    or switching assets.
    """
    def __init__(self, project_templates):
        super(SubstanceProjectConfigurationWindow, self).__init__()
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)

        self.import_cameras = False
        self.preserve_strokes = False
        self.template_name = None
        self.project_templates = project_templates

        self.widgets = {
            "label": QtWidgets.QLabel("Project Configuration"),
            "template_options": QtWidgets.QComboBox(),
            "import_cameras": QtWidgets.QCheckBox("Improve Cameras"),
            "preserve_strokes": QtWidgets.QCheckBox("Preserve Strokes"),
            "clickbox": QtWidgets.QWidget(),
            "combobox": QtWidgets.QWidget(),
            "okButton": QtWidgets.QPushButton("Ok"),
        }
        for template in project_templates:
            self.widgets["template_options"].addItem(template)

        # Build clickboxes
        layout = QtWidgets.QHBoxLayout(self.widgets["clickbox"])
        layout.addWidget(self.widgets["import_cameras"])
        layout.addWidget(self.widgets["preserve_strokes"])
        # Build buttons.
        layout = QtWidgets.QHBoxLayout(self.widgets["combobox"])
        layout.addWidget(self.widgets["template_options"])
        layout.addWidget(self.widgets["okButton"])
        # Build layout.
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.widgets["label"])
        layout.addWidget(self.widgets["clickbox"])
        layout.addWidget(self.widgets["combobox"])

        self.widgets["okButton"].pressed.connect(self.on_ok_pressed)

    def on_ok_pressed(self):
        if self.widgets["import_cameras"].isChecked():
            self.import_cameras = True
        if self.widgets["preserve_strokes"].isChecked():
            self.preserve_strokes = True
        self.template_name = (
            self.widgets["template_options"].currentText()
        )
        self.close()


class SubstanceLoadProjectMesh(load.LoaderPlugin):
    """Load mesh for project"""

    families = ["*"]
    representations = ["abc", "fbx", "obj", "gltf"]

    label = "Load mesh"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, options=None):

        # Get user inputs
        template_enum = [template["name"] for template
                         in self.project_templates]
        window = SubstanceProjectConfigurationWindow(template_enum)
        window.exec_()
        template_name = window.template_name
        import_cameras = window.import_cameras
        preserve_strokes = window.preserve_strokes
        template = get_template_by_name(template_name, self.project_templates)
        sp_settings = substance_painter.project.Settings(
            normal_map_format=_convert(template["normal_map_format"]),
            project_workflow=_convert(template["project_workflow"]),
            tangent_space_mode=_convert(template["tangent_space_mode"]),
            default_texture_resolution=template["default_texture_resolution"]
        )
        if not substance_painter.project.is_open():
            # Allow to 'initialize' a new project
            path = self.filepath_from_context(context)
            settings = substance_painter.project.create(
                mesh_file_path=path, settings=sp_settings
            )

        else:
            # Reload the mesh
            settings = substance_painter.project.MeshReloadingSettings(
                import_cameras=import_cameras,
                preserve_strokes=preserve_strokes)

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
