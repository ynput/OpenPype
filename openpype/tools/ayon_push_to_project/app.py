import click

from openpype.tools.utils import get_openpype_qt_app
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

    app = get_openpype_qt_app()

    window = PushToContextSelectWindow()
    window.show()
    window.controller.set_source(project, version)

    app.exec_()


if __name__ == "__main__":
    main()
