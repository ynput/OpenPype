from openpype import OP4_TEST_ENABLED

if not OP4_TEST_ENABLED:
    from .mongo.entities import *
else:
    from .server.entities import *
