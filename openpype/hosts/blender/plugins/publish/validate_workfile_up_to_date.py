import pyblish.api
import bpy

from openpype.hosts.blender.api.pipeline import (
    check_workfile_up_to_date,
)


class ValidateWorkfileUpToDate(pyblish.api.Validator):
    """Validate that the current workfile is up to date."""

    hosts = ["blender"]
    families = ["workfile"]
    label = "Validate Workfile Up To Date"
    optional = True

    def process(self):
        if (
            not check_workfile_up_to_date()
            or bpy.context.window_manager.is_workfile_out_of_date
        ):
            raise RuntimeError(
                "Current workfile is out of date! "
                "Please download last workfile."
            )
