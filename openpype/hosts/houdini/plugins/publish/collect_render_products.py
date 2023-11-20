import re
import os

import hou
import pxr.UsdRender

import pyblish.api


def get_var_changed(variable=None):
    """Return changed variables and operators that use it.

    Note: `varchange` hscript states that it forces a recook of the nodes
          that use Variables. That was tested in Houdini
          18.0.391.

    Args:
        variable (str, Optional): A specific variable to query the operators
            for. When None is provided it will return all variables that have
            had recent changes and require a recook. Defaults to None.

    Returns:
        dict: Variable that changed with the operators that use it.

    """
    cmd = "varchange -V"
    if variable:
        cmd += " {0}".format(variable)
    output, _ = hou.hscript(cmd)

    changed = {}
    for line in output.split("Variable: "):
        if not line.strip():
            continue

        split = line.split()
        var = split[0]
        operators = split[1:]
        changed[var] = operators

    return changed


class CollectRenderProducts(pyblish.api.InstancePlugin):
    """Collect USD Render Products.

    This collects the Render Products from the USD Render ROP's defined
    render settings.

    """

    label = "Collect Render Products"
    order = pyblish.api.CollectorOrder + 0.4
    hosts = ["houdini"]
    families = ["usdrender"]

    def process(self, instance):

        node = instance.data.get("output_node")
        rop_path = instance.data["instance_node"]
        if not node:
            raise RuntimeError(
                "No output node found. Make sure to connect an "
                "input to the USD ROP: %s" % rop_path
            )

        rop_node = hou.node(rop_path)

        # Workaround Houdini 18.0.391 bug where $HIPNAME doesn't automatically
        # update after scene save.
        if hou.applicationVersion() == (18, 0, 391):
            self.log.debug(
                "Checking for recook to workaround " "$HIPNAME refresh bug..."
            )
            changed = get_var_changed("HIPNAME").get("HIPNAME")
            if changed:
                self.log.debug("Recooking for $HIPNAME refresh bug...")
                for operator in changed:
                    hou.node(operator).cook(force=True)

                # Make sure to recook any 'cache' nodes in the history chain
                chain = [node]
                chain.extend(node.inputAncestors())
                for input_node in chain:
                    if input_node.type().name() == "cache":
                        input_node.cook(force=True)

        stage = node.stage()

        # Houdini docs state about the `rendersettings` parm:
        #  If this is blank, the node looks for default render settings
        #  on the root prim. If the root prim has no render settings,
        #  the node will use default settings.
        # TODO: Allow empty value to fallback to defaults
        render_settings_prim_path = rop_node.evalParm("rendersettings")
        render_settings_prim = stage.GetPrimAtPath(render_settings_prim_path)
        if not render_settings_prim:
            self.log.error(
                "RenderSettings prim '%s' not found for USD Render ROP '%s'",
                render_settings_prim_path, rop_path
            )
            return

        render_settings = pxr.UsdRender.Settings(render_settings_prim)
        products = render_settings.GetProductsRel().GetTargets()
        if not products:
            self.log.warning(
                "RenderSettings prim '%s' do not have any render products "
                "for USD Render ROP '%s'",
                render_settings_prim_path, rop_path
            )

        filenames = []
        for product in products:

            # We force taking it from any random time sample as opposed to
            # "default" that the USD Api falls back to since that won't return
            # time sampled values if they were set per time sample.
            name = product.GetProductNameAttr().Get(time=0)
            dirname = os.path.dirname(name)
            basename = os.path.basename(name)

            dollarf_regex = r"(\$F([0-9]?))"
            frame_regex = r"^(.+\.)([0-9]+)(\.[a-zA-Z]+)$"
            if re.match(dollarf_regex, basename):
                # TODO: Confirm this actually is allowed USD stages and HUSK
                # Substitute $F
                def replace(match):
                    """Replace $F4 with padded #."""
                    padding = int(match.group(2)) if match.group(2) else 1
                    return "#" * padding

                filename_base = re.sub(dollarf_regex, replace, basename)
                filename = os.path.join(dirname, filename_base)
            else:
                # Substitute basename.0001.ext
                def replace(match):
                    prefix, frame, ext = match.groups()
                    padding = "#" * len(frame)
                    return prefix + padding + ext

                filename_base = re.sub(frame_regex, replace, basename)
                filename = os.path.join(dirname, filename_base)
                filename = filename.replace("\\", "/")

            assert "#" in filename, (
                "Couldn't resolve render product name "
                "with frame number: %s" % name
            )

            filenames.append(filename)

            # TODO: Report the product's prim path?
            self.log.info("Collected %s name: %s" % (product, filename))

        # Filenames for Deadline
        instance.data["files"] = filenames
