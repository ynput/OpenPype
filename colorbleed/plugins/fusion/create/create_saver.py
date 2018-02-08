import avalon.api
from avalon import fusion


class CreateTiffSaver(avalon.api.Creator):

    name = "tiffDefault"
    label = "Create Tiff Saver"
    hosts = "fusion"
    family = "colorbleed.imagesequence"

    def process(self):

        comp = fusion.get_current_comp()
        with fusion.comp_lock_and_undo_chunk(comp):
            args = (-32768, -32768)  # Magical position numbers
            saver = comp.AddTool("Saver", *args)
            saver.SetAttrs({
                "TOOLS_Name": self.data.get("name", self.name),
                'TOOLST_Clip_FormatID': {1.0: 'TiffFormat'},
            })
