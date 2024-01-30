# -*- coding: utf-8 -*-
"""Export stuff in render setup layer context.

Export Maya nodes from Render Setup layer as if flattened in that layer instead
of exporting the defaultRenderLayer as Maya forces by default

Credits: Roy Nieterau (BigRoy) / Colorbleed
Modified for use in OpenPype

"""

import os
import contextlib

from maya import cmds
from maya.app.renderSetup.model import renderSetup

from .lib import pairwise


@contextlib.contextmanager
def _allow_export_from_render_setup_layer():
    """Context manager to override Maya settings to allow RS layer export"""
    try:

        rs = renderSetup.instance()

        # Exclude Render Setup nodes from the export
        rs._setAllRSNodesDoNotWrite(True)

        # Disable Render Setup forcing the switch to master layer
        os.environ["MAYA_BATCH_RENDER_EXPORT"] = "1"

        yield

    finally:
        # Reset original state
        rs._setAllRSNodesDoNotWrite(False)
        os.environ.pop("MAYA_BATCH_RENDER_EXPORT", None)


def export_in_rs_layer(path, nodes, export=None):
    """Export nodes from Render Setup layer.

    When exporting from Render Setup layer Maya by default
    forces a switch to the defaultRenderLayer as such making
    it impossible to export the contents of a Render Setup
    layer. Maya presents this warning message:
        # Warning: Exporting Render Setup master layer content #

    This function however avoids the renderlayer switch and
    exports from the Render Setup layer as if the edits were
    'flattened' in the master layer.

    It does so by:
        - Allowing export from Render Setup Layer
        - Enforce Render Setup nodes to NOT be written on export
        - Disconnect connections from any `applyOverride` nodes
          to flatten the values (so they are written correctly)*
    *Connection overrides like Shader Override and Material
    Overrides export correctly out of the box since they don't
    create an intermediate connection to an 'applyOverride' node.
    However, any scalar override (absolute or relative override)
    will get input connections in the layer so we'll break those
    to 'store' the values on the attribute itself and write value
    out instead.

    Args:
        path (str): File path to export to.
        nodes (list): Maya nodes to export.
        export (callable, optional): Callback to be used for exporting. If
            not specified, default export to `.ma` will be called.

    Returns:
        None

    Raises:
        AssertionError: When not in a Render Setup layer an
            AssertionError is raised. This command assumes
            you are currently in a Render Setup layer.

    """
    rs = renderSetup.instance()
    assert rs.getVisibleRenderLayer().name() != "defaultRenderLayer", \
        ("Export in Render Setup layer is only supported when in "
         "Render Setup layer")

    # Break connection to any value overrides
    history = cmds.listHistory(nodes) or []
    nodes_all = list(
        set(cmds.ls(nodes + history, long=True, objectsOnly=True)))
    overrides = cmds.listConnections(nodes_all,
                                     source=True,
                                     destination=False,
                                     type="applyOverride",
                                     plugs=True,
                                     connections=True) or []
    for dest, src in pairwise(overrides):
        # Even after disconnecting the values
        # should be preserved as they were
        # Note: animated overrides would be lost for export
        cmds.disconnectAttr(src, dest)

    # Export Selected
    with _allow_export_from_render_setup_layer():
        cmds.select(nodes, noExpand=True)
        if export:
            export()
        else:
            cmds.file(path,
                      force=True,
                      typ="mayaAscii",
                      exportSelected=True,
                      preserveReferences=False,
                      channels=True,
                      constraints=True,
                      expressions=True,
                      constructionHistory=True)

    if overrides:
        # If we have broken override connections then Maya
        # is unaware that the Render Setup layer is in an
        # invalid state. So let's 'hard reset' the state
        # by going to default render layer and switching back
        layer = rs.getVisibleRenderLayer()
        rs.switchToLayer(None)
        rs.switchToLayer(layer)
