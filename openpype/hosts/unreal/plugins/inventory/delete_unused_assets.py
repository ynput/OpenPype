import unreal

from openpype.hosts.unreal.api.tools_ui import qt_app_context
from openpype.hosts.unreal.api.pipeline import delete_asset_if_unused
from openpype.pipeline import InventoryAction


class DeleteUnusedAssets(InventoryAction):
    """Delete all the assets that are not used in any level.
    """

    label = "Delete Unused Assets"
    icon = "trash"
    color = "red"
    order = 1

    dialog = None

    def _delete_unused_assets(self, containers):
        allowed_families = ["model", "rig"]

        for container in containers:
            container_dir = container.get("namespace")
            if container.get("family") not in allowed_families:
                unreal.log_warning(
                    f"Container {container_dir} is not supported.")
                continue

            asset_content = unreal.EditorAssetLibrary.list_assets(
                container_dir, recursive=True, include_folder=False
            )

            delete_asset_if_unused(container, asset_content)

    def _show_confirmation_dialog(self, containers):
        from qtpy import QtCore
        from openpype.widgets import popup
        from openpype.style import load_stylesheet

        dialog = popup.Popup()
        dialog.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.WindowStaysOnTopHint
        )
        dialog.setFocusPolicy(QtCore.Qt.StrongFocus)
        dialog.setWindowTitle("Delete all unused assets")
        dialog.setMessage(
            "You are about to delete all the assets in the project that \n"
            "are not used in any level. Are you sure you want to continue?"
        )
        dialog.setButtonText("Delete")

        dialog.on_clicked.connect(
            lambda: self._delete_unused_assets(containers)
        )

        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.setStyleSheet(load_stylesheet())

        self.dialog = dialog

    def process(self, containers):
        with qt_app_context():
            self._show_confirmation_dialog(containers)
