"""
Requires:
    context > comment
    context > ftrackSession
    instance > ftrackIntegratedAssetVersionsData
"""

import sys
import os
import re
import six

import pyblish.api
from openpype.settings import get_current_project_settings


class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


class IntegrateFtrackFromWorkfile(pyblish.api.InstancePlugin):
    """Add source workfile to AssetVersions in Ftrack."""

    # Must be after integrate asset new
    order = pyblish.api.IntegratorOrder + 0.4999
    label = "Integrate Ftrack source workfile"
    families = ["ftrack"]
    optional = True

    def process(self, instance):
        # Check if there are any integrated AssetVersion entities
        asset_versions_key = "ftrackIntegratedAssetVersionsData"
        asset_versions_data_by_id = instance.data.get(asset_versions_key)
        if not asset_versions_data_by_id:
            self.log.info("There are any integrated AssetVersions")
            return

        workfile_template = get_current_project_settings()["ftrack"]["publish"]["IntegrateFtrackFromWorkfile"]["source_filename"]  # noqa
        context = instance.context
        filename = context.data["currentFile"]
        filename = os.path.basename(filename)
        source = self.get_workfile_name(instance, filename, workfile_template)

        session = instance.context.data["ftrackSession"]
        for asset_version_data in asset_versions_data_by_id.values():
            asset_version = asset_version_data["asset_version"]
            asset_version["custom_attributes"]["fix_fromworkfile"] = source

            try:
                session.commit()
                self.log.debug("Source workfile: {} added to AssetVersion \"{}\"".format(
                    source, str(asset_version)
                ))
            except Exception:
                tp, value, tb = sys.exc_info()
                session.rollback()
                session._configure_locations()
                six.reraise(tp, value, tb)

    def get_workfile_name(self, instance, filename, workfile_template):
        context = instance.context
        basename, ext = os.path.splitext(filename)
        version = "v" + str(instance.data.get("version")).zfill(3)
        subversion = basename.split("_")[-1]
        if re.match(r'^v[0-9]+$', subversion):
            # If the last part of the filename is the version,
            # this means there is no subversion (a.k.a comment).
            # Lets clear the variable
            subversion = ""

        anatomy_data = context.data.get("anatomyData")

        formatting_data = {
            "asset": anatomy_data.get("asset"),
            "task": anatomy_data.get("task"),
            "subset": instance.data.get("subset"),
            "version": version,
            "project": anatomy_data.get("project"),
            "family": instance.data.get("family"),
            "comment": instance.data.get("comment"),
            "subversion": subversion,
            "inst_name": instance.data.get("name"),
            "ext": ext[1:]
        }

        try:
            custom_name = workfile_template.format_map(
                SafeDict(**formatting_data)
            )

            for m in re.finditer("__", custom_name):
                custom_name_list = list(custom_name)
                custom_name_list.pop(m.start())
                custom_name = "".join(custom_name_list)

            basename, ext = os.path.splitext(custom_name)
            if basename.endswith("_"):
                custom_name = "".join([basename[:-1], ext])
        except Exception as e:
            raise KeyError(
                "OpenPype Studio Settings (Deadline section): Syntax issue(s) "
                "in \"Job Name\" or \"Batch Name\" for the current project.\n"
                "Error: {}".format(e)
            )

        return custom_name
