"""
Temporary folder operations
"""

import os
import tempfile
from openpype.lib import StringTemplate
from openpype.pipeline import Anatomy


def get_temp_dir(
        project_name=None,
        anatomy=None,
        prefix=None, suffix=None,
        make_local=False
):
    """Get temporary dir path.

    If `make_local` is set, tempdir will be created in local tempdir.
    If `anatomy` is not set, default anatomy will be used.
    If `prefix` or `suffix` is not set, default values will be used.

    It also supports `OPENPYPE_TMPDIR`, so studio can define own temp
    shared repository per project or even per more granular context.
    Template formatting is supported also with optional keys. Folder is
    created in case it doesn't exists.

    Available anatomy formatting keys:
        - root[work | <root name key>]
        - project[name | code]

    Note:
        Staging dir does not have to be necessarily in tempdir so be careful
        about its usage.

    Args:
        project_name (str)[optional]: Name of project.
        anatomy (openpype.pipeline.Anatomy)[optional]: Anatomy object.
        make_local (bool)[optional]: If True, temp dir will be created in
            local tempdir.
        suffix (str)[optional]: Suffix for tempdir.
        prefix (str)[optional]: Prefix for tempdir.

    Returns:
        str: Path to staging dir of instance.
    """
    prefix = prefix or "op_tmp_"
    suffix = suffix or ""

    if make_local:
        return _create_local_staging_dir(prefix, suffix)

    # make sure anatomy is set
    if not anatomy:
        anatomy = Anatomy(project_name)

    # get customized tempdir path from `OPENPYPE_TMPDIR` env var
    custom_temp_dir = _create_custom_tempdir(
        anatomy.project_name, anatomy)

    if custom_temp_dir:
        return os.path.normpath(
            tempfile.mkdtemp(
                prefix=prefix,
                suffix=suffix,
                dir=custom_temp_dir
            )
        )
    else:
        return _create_local_staging_dir(prefix, suffix)


def _create_local_staging_dir(prefix, suffix):
    return os.path.normpath(
        tempfile.mkdtemp(
            prefix=prefix,
            suffix=suffix
        )
    )


def _create_custom_tempdir(project_name, anatomy=None):
    """ Create custom tempdir

    Template path formatting is supporting:
    - optional key formatting
    - available keys:
        - root[work | <root name key>]
        - project[name | code]

    Args:
        project_name (str): project name
        anatomy (openpype.pipeline.Anatomy)[optional]: Anatomy object

    Returns:
        str | None: formatted path or None
    """
    openpype_tempdir = os.getenv("OPENPYPE_TMPDIR")
    if not openpype_tempdir:
        return

    custom_tempdir = None
    if "{" in openpype_tempdir:
        if anatomy is None:
            anatomy = Anatomy(project_name)
        # create base formate data
        formatting_data = {
            "root": anatomy.roots,
            "project": {
                "name": anatomy.project_name,
                "code": anatomy.project_code,
            }
        }
        # path is anatomy template
        custom_tempdir = StringTemplate.format_template(
            openpype_tempdir, formatting_data).normalized()

    else:
        # path is absolute
        custom_tempdir = openpype_tempdir

    # create the dir path if it doesn't exists
    if not os.path.exists(custom_tempdir):
        try:
            # create it if it doesn't exists
            os.makedirs(custom_tempdir)
        except IOError as error:
            raise IOError(
                "Path couldn't be created: {}".format(error))

    return custom_tempdir
