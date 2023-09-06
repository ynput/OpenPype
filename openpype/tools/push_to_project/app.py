import click
from qtpy import QtWidgets, QtCore

from openpype.tools.push_to_project.window import PushToContextSelectWindow


@click.command()
@click.option("--project", help="Source project name")
@click.option("--version", help="Source version id")
def main(project, version):
    """Run PushToProject tool to integrate version in different project.

    Args:
        project (str): Source project name.
        version (str): Version id.
    """

    app = QtWidgets.QApplication.instance()
    if not app:
        # 'AA_EnableHighDpiScaling' must be set before app instance creation
        high_dpi_scale_attr = getattr(
            QtCore.Qt, "AA_EnableHighDpiScaling", None
        )
        if high_dpi_scale_attr is not None:
            QtWidgets.QApplication.setAttribute(high_dpi_scale_attr)

        app = QtWidgets.QApplication([])

    attr = getattr(QtCore.Qt, "AA_UseHighDpiPixmaps", None)
    if attr is not None:
        app.setAttribute(attr)

    window = PushToContextSelectWindow()
    window.show()
    window.controller.set_source(project, version)

    app.exec_()


if __name__ == "__main__":
    main()
