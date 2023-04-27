from openpype import AYON_SERVER_ENABLED

if not AYON_SERVER_ENABLED:
    from .mongo.entity_links import *
else:
    from .server.entity_links import *
