from .lib import update_global_session_from_doc

def OnDocumentChanged():
    update_global_session_from_doc()