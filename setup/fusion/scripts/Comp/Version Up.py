import colorbleed.lib
import avalon.fusion

attrs = comp.GetAttrs()
filename = comp.MapPath(attrs["COMPS_FileName"])
if not filename:
    raise RuntimeError("File not saved yet. Can't increment version.")
    
new = colorbleed.lib.version_up(filename)
print("Incrementing comp to: {}".format(new))

with avalon.fusion.comp_lock_and_undo_chunk(comp, "Save incrementally.."):
    comp.Save(new)