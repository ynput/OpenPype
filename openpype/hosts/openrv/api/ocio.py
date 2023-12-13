"""Helper functions to apply OCIO colorspace settings on groups.

This tries to set the relevant OCIO settings on the group's look and render
pipeline similar to what the OpenColorIO Basic Color Management package does in
OpenRV through its `ocio_source_setup` python file.

This assumes that the OpenColorIO Basic Color Management package of RV is both
installed and loaded.

"""
import rv.commands
import rv.qtutils

from .lib import (
    group_member_of_type,
    active_view
)


class OCIONotActiveForGroup(RuntimeError):
    """Error raised when OCIO is not enabled on the group node."""


def get_group_ocio_look_node(group):
    """Return OCIOLook node from source group"""
    pipeline = group_member_of_type(group, "RVLookPipelineGroup")
    if pipeline:
        return group_member_of_type(pipeline, "OCIOLook")


def get_group_ocio_file_node(group):
    """Return OCIOFile node from source group"""
    pipeline = group_member_of_type(group, "RVLinearizePipelineGroup")
    if pipeline:
        return group_member_of_type(pipeline, "OCIOFile")


def set_group_ocio_colorspace(group, colorspace):
    """Set the group's OCIOFile node ocio.inColorSpace property.

    This only works if OCIO is already 'active' for the group. T

    """
    import ocio_source_setup    # noqa, RV OCIO package
    node = get_group_ocio_file_node(group)

    if not node:
        raise OCIONotActiveForGroup(
            "Unable to find OCIOFile node for {}".format(group)
        )

    rv.commands.setStringProperty(
        f"{node}.ocio.inColorSpace", [colorspace], True
    )


def set_current_ocio_active_state(state):
    """Set the OCIO state for the currently active source.

    This is a hacky workaround to enable/disable the OCIO active state for
    a source since it appears to be that there's no way to explicitly trigger
    this callback from the `ocio_source_setup.OCIOSourceSetupMode` instance
    which does these changes.

    """
    # TODO: Make this logic less hacky
    # See: https://community.shotgridsoftware.com/t/how-to-enable-disable-ocio-and-set-ocio-colorspace-for-group-using-python/17178  # noqa

    group = rv.commands.viewNode()
    ocio_node = get_group_ocio_file_node(group)
    if state == bool(ocio_node):
        # Already in correct state
        return

    window = rv.qtutils.sessionWindow()
    menu_bar = window.menuBar()
    for action in menu_bar.actions():
        if action.text() != "OCIO" or action.toolTip() != "OCIO":
            continue

        ocio_menu = action.menu()

        for ocio_action in ocio_menu.actions():
            if ocio_action.toolTip() == "File Color Space":
                # The first entry is for "current source" instead
                # of all sources so we need to break the for loop
                # The first action of the file color space menu
                # is the "Active" action. So lets take that one
                active_action = ocio_action.menu().actions()[0]

                active_action.trigger()
                return

    raise RuntimeError(
        "Unable to set active state for current source. Make "
        "sure the OCIO package is installed and loaded."
    )


def set_group_ocio_active_state(group, state):
    """Set the OCIO state for the 'currently active source'.

    This is a hacky workaround to enable/disable the OCIO active state for
    a source since it appears to be that there's no way to explicitly trigger
    this callback from the `ocio_source_setup.OCIOSourceSetupMode` instance
    which does these changes.

    """
    ocio_node = get_group_ocio_file_node(group)
    if state == bool(ocio_node):
        # Already in correct state
        return

    with active_view(group):
        set_current_ocio_active_state(state)
