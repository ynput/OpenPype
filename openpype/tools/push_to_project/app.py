import click

from openpype.tools.utils import get_openpype_qt_app
from openpype.tools.push_to_project.window import PushToContextSelectWindow


def show(project, version, library_filter, context_only):
    window = PushToContextSelectWindow(
        library_filter=library_filter, context_only=context_only
    )
    window.show()
    window.controller.set_source(project, version)

    if __name__ == "__main__":
        app = get_openpype_qt_app()
        app.exec_()
    else:
        window.exec_()

    return window.context


@click.command()
@click.option("--project", help="Source project name")
@click.option("--version", help="Source version id")
def main(project, version):
    """Run PushToProject tool to integrate version in different project.

    Args:
        project (str): Source project name.
        version (str): Version id.
        version (bool): Filter to library projects only.
    """
    show(project, version, True, False)


if __name__ == "__main__":
    main()
