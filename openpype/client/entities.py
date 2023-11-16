from openpype import AYON_SERVER_ENABLED

if not AYON_SERVER_ENABLED:
    from .mongo.entities import *
else:
    from .server.entities import *
