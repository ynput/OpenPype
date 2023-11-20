import re
import os

import hou
from pxr import UsdRender

import pyblish.api


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

        stage = node.stage()

        # Initialize to empty for the case where render settings could
        # not be retrieved as intended
        files = instance.data.setdefault("files", [])

        # Houdini docs state about the `rendersettings` parm:
        #  If this is blank, the node looks for default render settings
        #  on the root prim. If the root prim has no render settings,
        #  the node will use default settings.
        # Also see:
        #  https://github.com/sideeffects/HoudiniUsdBridge/blob/cab7aae818fc582db2890d640b8468f7fbf4865c/src/houdini/lib/H_USD/HUSD/XUSD_RenderSettings.C#L1005-L1033  # noqa
        render_settings_prim_path = rop_node.evalParm("rendersettings")
        if render_settings_prim_path:
            render_settings_prim = stage.GetPrimAtPath(
                render_settings_prim_path
            )
            if not render_settings_prim:
                self.log.error(
                    "RenderSettings prim '%s' not found for "
                    "USD Render ROP '%s'", render_settings_prim_path, rop_path
                )
                return
            render_settings = UsdRender.Settings(render_settings_prim)
        else:
            # Use stage default render settings
            render_settings = UsdRender.Settings.GetStageRenderSettings(stage)
            if not render_settings.GetPrim():

                self.log.error(
                    "No default render settings found for USD Render ROP '%s'."
                    " It is recommended to explicitly specify the Render "
                    "Settings on the `rendersettings` parm of the USD Render "
                    "ROP.",
                    rop_path
                )
                return
        product_paths = render_settings.GetProductsRel().GetTargets()
        if not product_paths:
            self.log.warning(
                "RenderSettings prim '%s' do not have any render products "
                "for USD Render ROP '%s'",
                render_settings_prim_path, rop_path
            )

        for product_path in product_paths:
            prim = stage.GetPrimAtPath(product_path)
            product = UsdRender.Product(prim)

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

            files.append(filename)

            self.log.info(
                "Collected '%s' name: %s", str(prim.GetPath()), filename
            )
