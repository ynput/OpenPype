import os
import difflib
import contextlib
from maya import cmds

from openpype.settings import get_project_settings
from openpype.pipeline import legacy_io
from openpype.pipeline.create import (
    legacy_create,
    get_legacy_creator_by_name,
)
import openpype.hosts.maya.api.plugin
from openpype.hosts.maya.api.lib import (
    maintained_selection,
    get_container_members
)


@contextlib.contextmanager
def preserve_modelpanel_cameras(container, log=None):
    """Preserve camera members of container in the modelPanels.

    This is used to ensure a camera remains in the modelPanels after updating
    to a new version.

    """

    # Get the modelPanels that used the old camera
    members = get_container_members(container)
    old_cameras = set(cmds.ls(members, type="camera", long=True))
    if not old_cameras:
        # No need to manage anything
        yield
        return

    panel_cameras = {}
    for panel in cmds.getPanel(type="modelPanel"):
        cam = cmds.ls(cmds.modelPanel(panel, query=True, camera=True),
                      long=True)

        # Often but not always maya returns the transform from the
        # modelPanel as opposed to the camera shape, so we convert it
        # to explicitly be the camera shape
        if cmds.nodeType(cam) != "camera":
            cam = cmds.listRelatives(cam,
                                     children=True,
                                     fullPath=True,
                                     type="camera")[0]
        if cam in old_cameras:
            panel_cameras[panel] = cam

    if not panel_cameras:
        # No need to manage anything
        yield
        return

    try:
        yield
    finally:
        new_members = get_container_members(container)
        new_cameras = set(cmds.ls(new_members, type="camera", long=True))
        if not new_cameras:
            return

        for panel, cam_name in panel_cameras.items():
            new_camera = None
            if cam_name in new_cameras:
                new_camera = cam_name
            elif len(new_cameras) == 1:
                new_camera = next(iter(new_cameras))
            else:
                # Multiple cameras in the updated container but not an exact
                # match detected by name. Find the closest match
                matches = difflib.get_close_matches(word=cam_name,
                                                    possibilities=new_cameras,
                                                    n=1)
                if matches:
                    new_camera = matches[0]  # best match
                    if log:
                        log.info("Camera in '{}' restored with "
                                 "closest match camera: {} (before: {})"
                                 .format(panel, new_camera, cam_name))

            if not new_camera:
                # Unable to find the camera to re-apply in the modelpanel
                continue

            cmds.modelPanel(panel, edit=True, camera=new_camera)


class ReferenceLoader(openpype.hosts.maya.api.plugin.ReferenceLoader):
    """Reference file"""

    families = ["model",
                "pointcache",
                "proxyAbc",
                "animation",
                "mayaAscii",
                "mayaScene",
                "setdress",
                "layout",
                "camera",
                "rig",
                "camerarig",
                "staticMesh",
                "skeletalMesh",
                "mvLook"]

    representations = ["ma", "abc", "fbx", "mb"]

    label = "Reference"
    order = -10
    icon = "code-fork"
    color = "orange"

    # Name of creator class that will be used to create animation instance
    animation_creator_name = "CreateAnimation"

    def process_reference(self, context, name, namespace, options):
        import maya.cmds as cmds
        import pymel.core as pm

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "model"

        group_name = "{}:_GRP".format(namespace)
        # True by default to keep legacy behaviours
        attach_to_root = options.get("attach_to_root", True)

        path = self.filepath_from_context(context)
        with maintained_selection():
            cmds.loadPlugin("AbcImport.mll", quiet=True)
            file_url = self.prepare_root_value(path,
                                               context["project"]["name"])
            nodes = cmds.file(file_url,
                              namespace=namespace,
                              sharedReferenceFile=False,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=attach_to_root,
                              groupName=group_name)

            shapes = cmds.ls(nodes, shapes=True, long=True)

            new_nodes = (list(set(nodes) - set(shapes)))

            # if there are cameras, try to lock their transforms
            self._lock_camera_transforms(new_nodes)

            current_namespace = pm.namespaceInfo(currentNamespace=True)

            if current_namespace != ":":
                group_name = current_namespace + ":" + group_name

            group_name = "|" + group_name

            self[:] = new_nodes

            if attach_to_root:
                group_node = pm.PyNode(group_name)
                roots = set()

                for node in new_nodes:
                    try:
                        roots.add(pm.PyNode(node).getAllParents()[-2])
                    except:  # noqa: E722
                        pass

                if family not in ["layout", "setdress",
                                  "mayaAscii", "mayaScene"]:
                    for root in roots:
                        root.setParent(world=True)

                group_node.zeroTransformPivots()
                for root in roots:
                    root.setParent(group_node)

                cmds.setAttr(group_name + ".displayHandle", 1)

                settings = get_project_settings(os.environ['AVALON_PROJECT'])
                colors = settings['maya']['load']['colors']
                c = colors.get(family)
                if c is not None:
                    group_node.useOutlinerColor.set(1)
                    group_node.outlinerColor.set(
                        (float(c[0]) / 255),
                        (float(c[1]) / 255),
                        (float(c[2]) / 255))

                cmds.setAttr(group_name + ".displayHandle", 1)
                # get bounding box
                bbox = cmds.exactWorldBoundingBox(group_name)
                # get pivot position on world space
                pivot = cmds.xform(group_name, q=True, sp=True, ws=True)
                # center of bounding box
                cx = (bbox[0] + bbox[3]) / 2
                cy = (bbox[1] + bbox[4]) / 2
                cz = (bbox[2] + bbox[5]) / 2
                # add pivot position to calculate offset
                cx = cx + pivot[0]
                cy = cy + pivot[1]
                cz = cz + pivot[2]
                # set selection handle offset to center of bounding box
                cmds.setAttr(group_name + ".selectHandleX", cx)
                cmds.setAttr(group_name + ".selectHandleY", cy)
                cmds.setAttr(group_name + ".selectHandleZ", cz)

            if family == "rig":
                self._post_process_rig(name, namespace, context, options)
            else:
                if "translate" in options:
                    cmds.setAttr(group_name + ".t", *options["translate"])
            return new_nodes

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        with preserve_modelpanel_cameras(container, log=self.log):
            super(ReferenceLoader, self).update(container, representation)

        # We also want to lock camera transforms on any new cameras in the
        # reference or for a camera which might have changed names.
        members = get_container_members(container)
        self._lock_camera_transforms(members)

    def _post_process_rig(self, name, namespace, context, options):

        output = next((node for node in self if
                       node.endswith("out_SET")), None)
        controls = next((node for node in self if
                         node.endswith("controls_SET")), None)

        assert output, "No out_SET in rig, this is a bug."
        assert controls, "No controls_SET in rig, this is a bug."

        # Find the roots amongst the loaded nodes
        roots = cmds.ls(self[:], assemblies=True, long=True)
        assert roots, "No root nodes in rig, this is a bug."

        asset = legacy_io.Session["AVALON_ASSET"]
        dependency = str(context["representation"]["_id"])

        self.log.info("Creating subset: {}".format(namespace))

        # Create the animation instance
        creator_plugin = get_legacy_creator_by_name(
            self.animation_creator_name
        )
        with maintained_selection():
            cmds.select([output, controls] + roots, noExpand=True)
            legacy_create(
                creator_plugin,
                name=namespace,
                asset=asset,
                options={"useSelection": True},
                data={"dependencies": dependency}
            )

    def _lock_camera_transforms(self, nodes):
        cameras = cmds.ls(nodes, type="camera")
        if not cameras:
            return

        # Check the Maya version, lockTransform has been introduced since
        # Maya 2016.5 Ext 2
        version = int(cmds.about(version=True))
        if version >= 2016:
            for camera in cameras:
                cmds.camera(camera, edit=True, lockTransform=True)
        else:
            self.log.warning("This version of Maya does not support locking of"
                             " transforms of cameras.")
