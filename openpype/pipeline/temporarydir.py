"""
Temporary folder operations
"""

import os
from openpype.lib import StringTemplate
from openpype.pipeline import Anatomy


def create_custom_tempdir(project_name, anatomy=None, formating_data=None):
    """ Create custom tempdir

    Template path formatting is supporting:
    - optional key formating
    - available keys:
        - root[work | <root name key>]
        - project[name | code]

    Args:
        project_name (str): name of project
        anatomy (openpype.pipeline.Anatomy): Anatomy object
        formating_data (dict): formating data used for filling template.

    Returns:
        bool | str: formated path or None
    """
    openpype_tempdir = os.getenv("OPENPYPE_TMPDIR")
    if not openpype_tempdir:
        return

    custom_tempdir = None
    if "{" in openpype_tempdir:
        if anatomy is None:
            anatomy = Anatomy(project_name)
        # create base formate data
        data = {
            "root": anatomy.roots
        }
        if formating_data is None:
            # We still don't have `project_code` on Anatomy...
            project_doc = anatomy.get_project_doc_from_cache(project_name)
            data["project"] = {
                "name": project_name,
                "code": project_doc["data"]["code"],
            }
        else:
            data["project"] = formating_data["project"]

        # path is anatomy template
        custom_tempdir = StringTemplate.format_template(
            openpype_tempdir, data).normalized()

    else:
        # path is absolute
        custom_tempdir = openpype_tempdir

    # create he dir path if it doesnt exists
    if not os.path.exists(custom_tempdir):
        try:
            # create it if it doesnt exists
            os.makedirs(custom_tempdir)
        except IOError as error:
            raise IOError("Path couldn't be created: {}".format(error))

    return custom_tempdir
