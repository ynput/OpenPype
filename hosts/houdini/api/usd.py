"""Houdini-specific USD Library functions."""

import contextlib
import logging

from Qt import QtWidgets, QtCore, QtGui

from openpype import style
from openpype.pipeline import legacy_io
from openpype.tools.utils.assets_widget import SingleSelectAssetsWidget

from pxr import Sdf


log = logging.getLogger(__name__)


class SelectAssetDialog(QtWidgets.QWidget):
    """Frameless assets dialog to select asset with double click.

    Args:
        parm: Parameter where selected asset name is set.
    """

    def __init__(self, parm):
        self.setWindowTitle("Pick Asset")
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Popup)

        assets_widget = SingleSelectAssetsWidget(legacy_io, parent=self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(assets_widget)

        assets_widget.double_clicked.connect(self._set_parameter)
        self._assets_widget = assets_widget
        self._parm = parm

    def _set_parameter(self):
        name = self._assets_widget.get_selected_asset_name()
        self._parm.set(name)
        self.close()

    def _on_show(self):
        pos = QtGui.QCursor.pos()
        # Select the current asset if there is any
        select_id = None
        name = self._parm.eval()
        if name:
            db_asset = legacy_io.find_one(
                {"name": name, "type": "asset"},
                {"_id": True}
            )
            if db_asset:
                select_id = db_asset["_id"]

        # Set stylesheet
        self.setStyleSheet(style.load_stylesheet())
        # Refresh assets (is threaded)
        self._assets_widget.refresh()
        # Select asset - must be done after refresh
        if select_id is not None:
            self._assets_widget.select_asset(select_id)

        # Show cursor (top right of window) near cursor
        self.resize(250, 400)
        self.move(self.mapFromGlobal(pos) - QtCore.QPoint(self.width(), 0))

    def showEvent(self, event):
        super(SelectAssetDialog, self).showEvent(event)
        self._on_show()


def pick_asset(node):
    """Show a user interface to select an Asset in the project

    When double clicking an asset it will set the Asset value in the
    'asset' parameter.

    """

    parm = node.parm("asset_name")
    if not parm:
        log.error("Node has no 'asset' parameter: %s", node)
        return

    # Construct a frameless popup so it automatically
    # closes when clicked outside of it.
    global tool
    tool = SelectAssetDialog(parm)
    tool.show()


def add_usd_output_processor(ropnode, processor):
    """Add USD Output Processor to USD Rop node.

    Args:
        ropnode (hou.RopNode): The USD Rop node.
        processor (str): The output processor name. This is the basename of
            the python file that contains the Houdini USD Output Processor.

    """

    import loputils

    loputils.handleOutputProcessorAdd(
        {
            "node": ropnode,
            "parm": ropnode.parm("outputprocessors"),
            "script_value": processor,
        }
    )


def remove_usd_output_processor(ropnode, processor):
    """Removes USD Output Processor from USD Rop node.

    Args:
        ropnode (hou.RopNode): The USD Rop node.
        processor (str): The output processor name. This is the basename of
            the python file that contains the Houdini USD Output Processor.

    """
    import loputils

    parm = ropnode.parm(processor + "_remove")
    if not parm:
        raise RuntimeError(
            "Output Processor %s does not "
            "exist on %s" % (processor, ropnode.name())
        )

    loputils.handleOutputProcessorRemove({"node": ropnode, "parm": parm})


@contextlib.contextmanager
def outputprocessors(ropnode, processors=tuple(), disable_all_others=True):
    """Context manager to temporarily add Output Processors to USD ROP node.

    Args:
        ropnode (hou.RopNode): The USD Rop node.
        processors (tuple or list): The processors to add.
        disable_all_others (bool, Optional): Whether to disable all
            output processors currently on the ROP node that are not in the
            `processors` list passed to this function.

    """
    # TODO: Add support for forcing the correct Order of the processors

    original = []
    prefix = "enableoutputprocessor_"
    processor_parms = ropnode.globParms(prefix + "*")
    for parm in processor_parms:
        original.append((parm, parm.eval()))

    if disable_all_others:
        for parm in processor_parms:
            parm.set(False)

    added = []
    for processor in processors:

        parm = ropnode.parm(prefix + processor)
        if parm:
            # If processor already exists, just enable it
            parm.set(True)

        else:
            # Else add the new processor
            add_usd_output_processor(ropnode, processor)
            added.append(processor)

    try:
        yield
    finally:

        # Remove newly added processors
        for processor in added:
            remove_usd_output_processor(ropnode, processor)

        # Revert to original values
        for parm, value in original:
            if parm:
                parm.set(value)


def get_usd_rop_loppath(node):

    # Get sop path
    node_type = node.type().name()
    if node_type == "usd":
        return node.parm("loppath").evalAsNode()

    elif node_type in {"usd_rop", "usdrender_rop"}:
        # Inside Solaris e.g. /stage (not in ROP context)
        # When incoming connection is present it takes it directly
        inputs = node.inputs()
        if inputs:
            return inputs[0]
        else:
            return node.parm("loppath").evalAsNode()


def get_layer_save_path(layer):
    """Get custom HoudiniLayerInfo->HoudiniSavePath from SdfLayer.

    Args:
        layer (pxr.Sdf.Layer): The Layer to retrieve the save pah data from.

    Returns:
        str or None: Path to save to when data exists.

    """
    hou_layer_info = layer.rootPrims.get("HoudiniLayerInfo")
    if not hou_layer_info:
        return

    save_path = hou_layer_info.customData.get("HoudiniSavePath", None)
    if save_path:
        # Unfortunately this doesn't actually resolve the full absolute path
        return layer.ComputeAbsolutePath(save_path)


def get_referenced_layers(layer):
    """Return SdfLayers for all external references of the current layer

    Args:
        layer (pxr.Sdf.Layer): The Layer to retrieve the save pah data from.

    Returns:
        list: List of pxr.Sdf.Layer that are external references to this layer

    """

    layers = []
    for layer_id in layer.GetExternalReferences():
        layer = Sdf.Layer.Find(layer_id)
        if not layer:
            # A file may not be in memory and is
            # referenced from disk. As such it cannot
            # be found. We will ignore those layers.
            continue

        layers.append(layer)

    return layers


def iter_layer_recursive(layer):
    """Recursively iterate all 'external' referenced layers"""

    layers = get_referenced_layers(layer)
    traversed = set(layers)  # Avoid recursion to itself (if even possible)
    traverse = list(layers)
    for layer in traverse:

        # Include children layers (recursion)
        children_layers = get_referenced_layers(layer)
        children_layers = [x for x in children_layers if x not in traversed]
        traverse.extend(children_layers)
        traversed.update(children_layers)

        yield layer


def get_configured_save_layers(usd_rop):

    lop_node = get_usd_rop_loppath(usd_rop)
    stage = lop_node.stage(apply_viewport_overrides=False)
    if not stage:
        raise RuntimeError(
            "No valid USD stage for ROP node: " "%s" % usd_rop.path()
        )

    root_layer = stage.GetRootLayer()

    save_layers = []
    for layer in iter_layer_recursive(root_layer):
        save_path = get_layer_save_path(layer)
        if save_path is not None:
            save_layers.append(layer)

    return save_layers
