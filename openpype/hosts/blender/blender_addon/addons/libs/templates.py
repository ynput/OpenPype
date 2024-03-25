import logging

import bpy

from openpype.pipeline import get_current_project_name
from openpype.pipeline.anatomy import Anatomy

from openpype.client import get_asset_by_name
from openpype.pipeline import (
    get_current_context,
    get_current_project_name,
    get_current_asset_name
)
from openpype.pipeline.context_tools import get_template_data_from_session
from openpype.pipeline.template_data import get_general_template_data
from openpype.pipeline.project_folders import get_project_settings, get_project_basic_paths, get_project_template_data
from openpype.pipeline.anatomy import Anatomy

from libs import paths


class Default(dict):
    def __missing__(self, key):
        return '{'+key+'}'


def _get_anatomy_roots_and_template(template_name):
    project_name = get_current_project_name()
    anatomy_object = Anatomy()
    playblast_anatomy = anatomy_object.templates.get(template_name)
    if not playblast_anatomy:
        logging.warning(f"Can't retrieve template named {template_name}. Check settings for {project_name}.")
        return None, None
    return anatomy_object.roots, anatomy_object.templates[template_name]



def _get_template_data(roots, **additional_data):
    template_data = get_template_data_from_session()
    template_data['root'] = roots

    for key, value in additional_data.items():
        if value is None: continue
        template_data[key] = value

    return template_data


def _set_template_version(anatomy_template, template_data):
    folder_template = anatomy_template.get('folder')

    if not folder_template:
        logging.warning(f"Information labelled 'folder' is needed for this template.")
        return None

    template_data['version'] = paths.get_next_version_number(
        filepath=folder_template.format(version=1, **template_data)
        )

    return True


def _format_template_data(anatomy_template, template_path_key, template_data):
    path_template = anatomy_template.get(template_path_key)
    if not path_template:
        logging.warning(f"Information labelled '{template_path_key}' is needed for this template.")
        return None

    return path_template.format_map(Default(template_data))


def get_playblast_path():
    anatomy_roots, anatomy_template = _get_anatomy_roots_and_template(
        template_name="playblast"
    )
    if not anatomy_roots and not anatomy_template:
        return None

    template_data = _get_template_data(
        roots=anatomy_roots,
        template=anatomy_template,
        template_path_key="path",
    )
    if not _set_template_version(
        anatomy_template=anatomy_template,
        template_data=template_data
    ): return None

    return _format_template_data(
        anatomy_template=anatomy_template,
        template_path_key='path',
        template_data=template_data
    )


def get_render_global_output_path():
    anatomy_roots, anatomy_template = _get_anatomy_roots_and_template(
        template_name="deadline_render"
    )
    if not anatomy_roots and not anatomy_template:
        return None

    template_data = _get_template_data(
        roots=anatomy_roots,
        template=anatomy_template,
        template_path_key="global_output",
    )

    return _format_template_data(
        anatomy_template=anatomy_template,
        template_path_key='global_output',
        template_data=template_data
    )


def get_render_node_output_path(render_layer_name=None):
    anatomy_roots, anatomy_template = _get_anatomy_roots_and_template(
        template_name="deadline_render"
    )
    if not anatomy_roots and not anatomy_template:
        return None

    template_data = _get_template_data(
        roots=anatomy_roots,
        template=anatomy_template,
        template_path_key="node_output",
        render_layer_name=render_layer_name,
    )

    if not _set_template_version(
        anatomy_template=anatomy_template,
        template_data=template_data
    ): return None

    return _format_template_data(
        anatomy_template=anatomy_template,
        template_path_key='node_output',
        template_data=template_data
    )
