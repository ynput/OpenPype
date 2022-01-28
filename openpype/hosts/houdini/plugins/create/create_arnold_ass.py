import hou

from avalon import houdini


class CreateArnoldAss(houdini.Creator):
    """Arnold .ass Archive"""

    label = "Arnold ASS"
    family = "ass"
    icon = "magic"
    defaults = ["Main"]

    def __init__(self, *args, **kwargs):
        super(CreateArnoldAss, self).__init__(*args, **kwargs)

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        self.data.update({"node_type": "arnold"})

    def process(self):
        node = super(CreateArnoldAss, self).process()

        basename = node.name()
        node.setName(basename + "_ASS", unique_name=True)

        # Hide Properties Tab on Arnold ROP since that's used
        # for rendering instead of .ass Archive Export
        parm_template_group = node.parmTemplateGroup()
        parm_template_group.hideFolder("Properties", True)
        node.setParmTemplateGroup(parm_template_group)

        parms = {
            # Render frame range
            "trange": 1,

            # Arnold ROP settings
            "ar_ass_file": '$HIP/pyblish/`chs("subset")`.$F4.ass.gz',
            "ar_ass_export_enable": 1
        }
        node.setParms(parms)

        # Lock the ASS export attribute
        node.parm("ar_ass_export_enable").lock(True)

        # Lock some Avalon attributes
        to_lock = ["family", "id"]
        for name in to_lock:
            parm = node.parm(name)
            parm.lock(True)
