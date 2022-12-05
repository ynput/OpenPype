import pyblish.api
import bpy

from openpype.hosts.blender.utility_scripts.is_workfile_out_of_date import (
    is_work_file_out_of_date,
)


class ValidateWorkfileUpToDate(pyblish.api.Validator):
    """Validate that the current workfile is up to date."""

    hosts = ["blender"]
    families = ["workfile"]
    label = "Validate Workfile Up To Date"
    optional = True

    def process(self):
        if (
            is_work_file_out_of_date()
            or bpy.context.window_manager.is_workfile_out_of_date
        ):
            raise RuntimeError(
                "Current workfile is out of date! "
                "Please download last workfile."
            )
