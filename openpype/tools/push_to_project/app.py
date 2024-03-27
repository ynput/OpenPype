import json

import click

from openpype.tools.utils import get_openpype_qt_app
from openpype.tools.push_to_project.window import PushToContextSelectWindow


@click.command()
@click.option("--project", help="Source project name")
@click.option("--version", help="Source version id")
@click.option("--library_filter", help="Filter to library projects only.")
@click.option("--context_only", help="Return new context only.")
def main(project, version, library_filter, context_only):
    """Run PushToProject tool to integrate version in different project.

    Args:
        project (str): Source project name.
        version (str): Version id.
        version (bool): Filter to library projects only.
    """
    app = get_openpype_qt_app()

    if library_filter is None:
        library_filter = True
    else:
        library_filter = library_filter == "True"

    if context_only is None:
        context_only = True
    else:
        context_only = context_only == "True"

    window = PushToContextSelectWindow(
        library_filter=library_filter, context_only=context_only
    )
    window.show()
    window.controller.set_source(project, version)

    app.exec_()

    print(json.dumps(window.context))


if __name__ == "__main__":
    main()
