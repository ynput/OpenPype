from openpype import OP4_TEST_ENABLED

from .operations_base import REMOVED_VALUE
if not OP4_TEST_ENABLED:
    from .mongo.operations import *
    OperationsSession = MongoOperationsSession
