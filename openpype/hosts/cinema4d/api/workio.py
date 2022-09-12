"""Host API required Work Files tool"""
import os
import c4d

from openpype.pipeline import HOST_WORKFILE_EXTENSIONS
from .lib import set_doc_session


def file_extensions():
    return HOST_WORKFILE_EXTENSIONS["cinema4d"]


def has_unsaved_changes(doc=None):
    if not doc:
        doc = c4d.documents.GetActiveDocument()
    return doc.GetChanged()


def save_file(filepath=None, doc=None):
    if not doc:
        doc = c4d.documents.GetActiveDocument()
    if filepath:
        doc.SetDocumentPath(os.path.dirname(filepath))
        doc.SetDocumentName(os.path.basename(filepath))
    
    c4d.CallCommand(12098) #save
    set_doc_session()


def open_file(filepath):
    fp = c4d.documents.LoadFile(filepath)
    return fp


def current_file():
    doc = c4d.documents.GetActiveDocument()
    current_name = doc.GetDocumentName()
    current_filepath = os.path.join(doc.GetDocumentPath(), current_name)
    if not current_filepath:
        return None

    return current_filepath


def work_root(session):
    work_dir = session["AVALON_WORKDIR"]

    scene_dir = session.get("AVALON_SCENEDIR")

    if scene_dir:
        return os.path.join(work_dir, scene_dir)
    else:
        return work_dir
