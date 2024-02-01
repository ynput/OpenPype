import click

from openpype.tools.utils import get_openpype_qt_app
from openpype.tools.ayon_push_to_project.ui import PushToContextSelectWindow


def main_show(project_name, version_id):
    app = get_openpype_qt_app()

    window = PushToContextSelectWindow()
    window.show()
    window.set_source(project_name, version_id)

    app.exec_()


@click.command()
@click.option("--project", help="Source project name")
@click.option("--version", help="Source version id")
def main(project, version):
    """Run PushToProject tool to integrate version in different project.

    Args:
        project (str): Source project name.
        version (str): Version id.
    """

    main_show(project, version)


if __name__ == "__main__":
    main()
