"""A set of commands that install overrides to Maya's UI"""

import maya.cmds as mc
import maya.mel as mel
from functools import partial
import logging


log = logging.getLogger(__name__)

COMPONENT_MASK_ORIGINAL = {}


def override_component_mask_commands():
    """Override component mask ctrl+click behavior.

    This implements special behavior for Maya's component
    mask menu items where a ctrl+click will instantly make
    it an isolated behavior disabling all others.
    
    Tested in Maya 2016 and 2018

    """
    log.info("Installing override_component_mask_commands..")

    # Get all object mask buttons
    buttons = mc.formLayout("objectMaskIcons",
                            query=True,
                            childArray=True)
    # Skip the triangle list item
    buttons = [btn for btn in buttons if btn != "objPickMenuLayout"]

    def on_changed_callback(raw_command, state):
        """New callback"""

        # If "control" is held force the toggled one to on and
        # toggle the others based on whether any of the buttons
        # was remaining active after the toggle, if not then
        # enable all
        if mc.getModifiers() == 4:  # = CTRL
            state = True
            active = [mc.iconTextCheckBox(btn, query=True, value=True) for btn
                      in buttons]
            if any(active):
                mc.selectType(allObjects=False)
            else:
                mc.selectType(allObjects=True)

        # Replace #1 with the current button state
        cmd = raw_command.replace(" #1", " {}".format(int(state)))
        mel.eval(cmd)

    for btn in buttons:

        # Store a reference to the original command so that if
        # we rerun this override command it doesn't recursively
        # try to implement the fix. (This also allows us to
        # "uninstall" the behavior later)
        if btn not in COMPONENT_MASK_ORIGINAL:
            original = mc.iconTextCheckBox(btn, query=True, cc=True)
            COMPONENT_MASK_ORIGINAL[btn] = original

        # Assign the special callback
        original = COMPONENT_MASK_ORIGINAL[btn]
        new_fn = partial(on_changed_callback, original)
        mc.iconTextCheckBox(btn, edit=True, cc=new_fn)
