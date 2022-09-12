import c4d
import contextlib

'''
C4D handles all imports and exports of file types through import/export plugins.
There is a special convoluted way to get the settings for the plugins by supplying
the plugin ID and getting a dict that with the settings that can be set.

By default exporters sticky the previous settings, so for consistency and reliability
set each possible setting each time. Use the exporter_settings statement to return the 
settings to their previous state.
'''

def get_export_settings(exporter_id):
    plug = c4d.plugins.FindPlugin(exporter_id, c4d.PLUGINTYPE_SCENESAVER)

    if plug is None:
        return

    settings_dict = {}

    if plug.Message(c4d.MSG_RETRIEVEPRIVATEDATA, settings_dict):
        if "imexporter" not in settings_dict:
            return
        
        exporter = settings_dict["imexporter"]

        if exporter is None:
            return

        return exporter

@contextlib.contextmanager
def exporter_settings(exporter_id, defaults={}):

    exporter = get_export_settings(exporter_id)
    if exporter:
        previous_settings = {}
        for key, value in defaults.items():
            previous_settings[key] = {"id":value["id"], "default":exporter[value["id"]]}
    else:
        previous_settings = None
    try:
        yield exporter
    finally:
        if previous_settings:
            for key, value in previous_settings.items():
                exporter[value["id"]] = value["default"]

def export_abc(filepath, settings={}, doc=None):
    if not doc:
        doc = c4d.documents.GetActiveDocument()

    defaults = {
        "selection_only": {
            "id": c4d.ABCEXPORT_SELECTION_ONLY,
            "default": False
        },
        "global": {
            "id": c4d.ABCEXPORT_GLOBAL_MATRIX,
            "default": False
        },
        "cameras": {
            "id": c4d.ABCEXPORT_CAMERAS,
            "default": True
        },
        "xrefs": {
            "id": c4d.ABCEXPORT_XREFS,
            "default": True
        },
        "sds": {
            "id": c4d.ABCEXPORT_HYPERNURBS,
            "default": True
        },
        "sds_weights": {
            "id": c4d.ABCEXPORT_HYPERNURBS,
            "default": True
        },
        "splines": {
            "id":c4d.ABCEXPORT_SPLINES,
            "default":False
        },
        "hair": {
            "id":c4d.ABCEXPORT_HAIR,
            "default":True
        },
        "particles": {
            "id":c4d.ABCEXPORT_PARTICLES,
            "default":False
        },
        "particles_geo": {
            "id":c4d.ABCEXPORT_PARTICLE_GEOMETRY,
            "default":False
        },
        "start": {
            "id":c4d.ABCEXPORT_FRAME_START,
            "default":0
        },
        "end": {
            "id":c4d.ABCEXPORT_FRAME_END,
            "default":0
        },
        "step": {
            "id":c4d.ABCEXPORT_FRAME_STEP,
            "default":1
        },
        "subframes": {
            "id":c4d.ABCEXPORT_SUBFRAMES,
            "default":1
        },
        "visibility": {
            "id":c4d.ABCEXPORT_VISIBILITY,
            "default":True
        },
        "selections": {
            "id":c4d.ABCEXPORT_POLYGONSELECTIONS,
            "default":True
        },
        "normals": {
            "id":c4d.ABCEXPORT_NORMALS,
            "default":True
        },
        "uvs": {
            "id":c4d.ABCEXPORT_UVS,
            "default":True
        },
        "vertex_colors": {
            "id":c4d.ABCEXPORT_VERTEX_COLORS,
            "default":True
        },
        "display_colors": {
            "id":c4d.ABCEXPORT_DISPLAY_COLORS,
            "default":False
        },
        "vertex_maps": {
            "id":c4d.ABCEXPORT_VERTEX_MAPS,
            "default":False
        },
        "points_only": {
            "id":c4d.ABCEXPORT_POINTS_ONLY,
            "default":False
        },
        "merge_generated": {
            "id":c4d.ABCEXPORT_MERGE_CACHE,
            "default":False
        }
    }


    with exporter_settings(c4d.FORMAT_ABCEXPORT, defaults) as exporter:

        for key, value in defaults.items():
            exporter[value["id"]] = settings.get(key) or value["default"]

        c4d.documents.SaveDocument(doc, filepath, c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_ABCEXPORT)