from openpype import OP4_TEST_ENABLED

if not OP4_TEST_ENABLED:
    from .mongo.entity_links import *
else:
    from .server.entity_links import *
