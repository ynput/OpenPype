import hou
import pyblish.api


class CollectHoudiniReviewData(pyblish.api.InstancePlugin):
    """Collect Review Data."""

    label = "Collect Review Data"
    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["houdini"]
    families = ["review"]

    def process(self, instance):

        # This fixes the burnin having the incorrect start/end timestamps
        # because without this it would take it from the context instead
        # which isn't the actual frame range that this instance renders.
        instance.data["handleStart"] = 0
        instance.data["handleEnd"] = 0

        # Get the camera from the rop node to collect the focal length
        start = instance.data["frameStart"]
        end = instance.data["frameEnd"] + 1
        ropnode_path = instance.data["instance_node"]
        ropnode = hou.node(ropnode_path)

        source = ropnode.parm("opsource").evalAsString()
        if source == "obj":
            self.log.debug("Processing Object mode..")
            # Object mode
            camera_path = ropnode.parm("camera").eval()
            camera_node = hou.node(camera_path)
            if not camera_node:
                self.log.warning("No valid camera node found on review node: "
                                 "{}".format(camera_path))
                return

            focal_length = self.get_obj_camera_focal_length(
                camera_node, start, end
            )

        elif source == "lop":
            self.log.debug("Processing LOPs mode..")
            # LOPs mode
            lop_node = ropnode.parm("loppath").evalAsNode()
            if not lop_node:
                # No valid node set
                self.log.debug("No valid LOP Path set..")
                return

            if not isinstance(lop_node, hou.LopNode):
                # No valid node set
                self.log.debug("Node '{}' it not a LopNode.".format(lop_node))
                # Not a LOP node
                return

            prim_path = ropnode.parm("cameraprim").evalAsString()
            focal_length = self.get_lop_camera_focal_length(
                lop_node, prim_path, start, end
            )
        else:
            raise ValueError("Unknown openGL render source: {}".format(source))

        if not focal_length:
            return

        self.log.debug(
            "Collected camera focal length: {}".format(focal_length)
        )

        # Store focal length in `burninDataMembers`
        burnin_members = instance.data.setdefault("burninDataMembers", {})
        burnin_members["focalLength"] = focal_length

        instance.data.setdefault("families", []).append('ftrack')

    def get_obj_camera_focal_length(self, camera_node, start, end):
        # Collect focal length.
        focal_length_parm = camera_node.parm("focal")
        if not focal_length_parm:
            camera_path = camera_node.path()
            self.log.warning("No 'focal' (focal length) parameter found on "
                             "camera: {}".format(camera_path))
            return

        if focal_length_parm.isTimeDependent():
            return [
                focal_length_parm.evalAsFloatAtFrame(t)
                for t in range(int(start), int(end))
            ]
        else:
            return focal_length_parm.evalAsFloat()

    def get_lop_camera_focal_length(self, lop_node, prim_path, start, end):
        """Get camera focal length values over time.

        We want to get the values over time, however LOPs actually builds
        the stage over time per frame unless there's a cache node. So getting
        the stage without a cache nodes basically means there are no time
        samples. As such, this would only query the time samples if the
        values are 'cached' previously.

        """
        # TODO: We could force Solaris to cache the full frame range by
        #   making a `cache` node and set it to Always cache all frames with
        #   the cache node's frame range set to the required frame range.
        #   However, this could still be massively slow since it's technically
        #   building the full frame range of USD content
        from pxr import Usd

        # somehow focal length values in are 100 times smaller in Solaris/USD
        # so 0.5 resembles 50mm focal length on the Camera LOP node.
        multiplier = 100

        stage = lop_node.stage()
        prim = stage.GetPrimAtPath(prim_path)
        if not prim:
            self.log.warning("Camera primitive not found at USD "
                             "prim path: {}".format(prim_path))
            return

        focal_length_property = prim.GetProperty("focalLength")
        if not focal_length_property:
            self.log.warning("Primitive {} does not have 'focalLength' "
                             "property.".format(prim_path))
            return

        if (
            not focal_length_property.HasAuthoredValue() or
            not focal_length_property.GetNumTimeSamples()
        ):
            # Static value
            start_time = Usd.TimeCode(start)
            return focal_length_property.Get(start_time) * multiplier
        else:
            # There are time based values
            return [
                focal_length_property.Get(Usd.TimeCode(t)) * multiplier
                for t in range(int(start), int(end))
            ]
