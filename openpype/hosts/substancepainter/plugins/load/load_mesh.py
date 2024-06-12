import copy
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

        self.configuration = None
        self.template_names = [template["name"] for template
                               in project_templates]
        self.project_templates = project_templates

        self.widgets = {
            "label": QtWidgets.QLabel(
                "Select your template for project configuration"),
            "template_options": QtWidgets.QComboBox(),
            "import_cameras": QtWidgets.QCheckBox("Import Cameras"),
            "preserve_strokes": QtWidgets.QCheckBox("Preserve Strokes"),
            "clickbox": QtWidgets.QWidget(),
            "combobox": QtWidgets.QWidget(),
            "buttons": QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok
                | QtWidgets.QDialogButtonBox.Cancel)
        }

        self.widgets["template_options"].addItems(self.template_names)

        template_name = self.widgets["template_options"].currentText()
        self._update_to_match_template(template_name)
        # Build clickboxes
        layout = QtWidgets.QHBoxLayout(self.widgets["clickbox"])
        layout.addWidget(self.widgets["import_cameras"])
        layout.addWidget(self.widgets["preserve_strokes"])
        # Build combobox
        layout = QtWidgets.QHBoxLayout(self.widgets["combobox"])
        layout.addWidget(self.widgets["template_options"])
        # Build buttons
        layout = QtWidgets.QHBoxLayout(self.widgets["buttons"])
        # Build layout.
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.widgets["label"])
        layout.addWidget(self.widgets["combobox"])
        layout.addWidget(self.widgets["clickbox"])
        layout.addWidget(self.widgets["buttons"])

        self.widgets["template_options"].currentTextChanged.connect(
            self._update_to_match_template)
        self.widgets["buttons"].accepted.connect(self.on_accept)
        self.widgets["buttons"].rejected.connect(self.on_reject)

    def on_accept(self):
        self.configuration = self.get_project_configuration()
        self.close()

    def on_reject(self):
        self.close()

    def _update_to_match_template(self, template_name):
        template = get_template_by_name(template_name, self.project_templates)
        self.widgets["import_cameras"].setChecked(template["import_cameras"])
        self.widgets["preserve_strokes"].setChecked(
            template["preserve_strokes"])

    def get_project_configuration(self):
        templates = self.project_templates
        template_name = self.widgets["template_options"].currentText()
        template = get_template_by_name(template_name, templates)
        template = copy.deepcopy(template)  # do not edit the original
        template["import_cameras"] = self.widgets["import_cameras"].isChecked()
        template["preserve_strokes"] = (
            self.widgets["preserve_strokes"].isChecked()
        )
        for key in ["normal_map_format",
                    "project_workflow",
                    "tangent_space_mode"]:
            template[key] = _convert(template[key])
        return template

    @classmethod
    def prompt(cls, templates):
        dialog = cls(templates)
        dialog.exec_()
        configuration = dialog.configuration
        dialog.deleteLater()
        return configuration


class SubstanceLoadProjectMesh(load.LoaderPlugin):
    """Load mesh for project"""

    families = ["*"]
    representations = ["abc", "fbx", "obj", "gltf"]

    label = "Load mesh"
    order = -10
    icon = "code-fork"
    color = "orange"

    # Defined via settings
    project_templates = []

    def load(self, context, name, namespace, options=None):

        # Get user inputs
        result = SubstanceProjectConfigurationWindow.prompt(
            self.project_templates)
        if not result:
            # cancelling loader action
            return
        sp_settings = substance_painter.project.Settings(
            import_cameras=result["import_cameras"],
            normal_map_format=result["normal_map_format"],
            project_workflow=result["project_workflow"],
            tangent_space_mode=result["tangent_space_mode"],
            default_texture_resolution=result["default_texture_resolution"]
        )
        if not substance_painter.project.is_open():
            # Allow to 'initialize' a new project
            path = self.filepath_from_context(context)
            sp_settings = substance_painter.project.Settings(
                import_cameras=result["import_cameras"],
                normal_map_format=result["normal_map_format"],
                project_workflow=result["project_workflow"],
                tangent_space_mode=result["tangent_space_mode"],
                default_texture_resolution=result["default_texture_resolution"]
            )
            settings = substance_painter.project.create(
                mesh_file_path=path, settings=sp_settings
            )
        else:
            # Reload the mesh
            settings = substance_painter.project.MeshReloadingSettings(
                import_cameras=result["import_cameras"],
                preserve_strokes=result["preserve_strokes"])

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
            "import_cameras": result["import_cameras"],
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
