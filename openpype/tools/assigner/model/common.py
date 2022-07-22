class AssignerToolSubModel(object):
    """Base submodel for assigner tool.

    Sub model cares about specific part of tool data source.
    """

    def __init__(self, main_model):
        self._main_model = main_model

    @property
    def project_name(self):
        return self._main_model.project_name

    @property
    def event_system(self):
        return self._main_model.event_system


def convert_document(doc):
    """Helper function for mongo document conversion.

    Mongo database use 'ObjectId' for ids which is unfortunatelly not helpful
    for sending information about them across tool. E.g. when is converted to
    string it changes the "identifier" value it had. Thus for tool usage
    are all ids converted to strings.

    Warning:
        Function does not create copy but modify passed object.

    Args:
        Dict[str, Any]: Source document queried from mongo database.

    Returns:
        Dict[str, Any]: Converted document.
    """

    doc["_id"] = str(doc["_id"])
    parent_id = doc.get("parent")
    if parent_id:
        doc["parent"] = str(parent_id)

    version_id = doc.get("version_id")
    if version_id:
        doc["version_id"] = str(version_id)

    if "data" in doc:
        doc_data = doc["data"]
        visual_parent = doc_data.get("visualParent")
        if visual_parent:
            doc_data["visualParent"] = str(visual_parent)

        thumbnail_id = doc_data.get("thumbnail_id")
        if thumbnail_id:
            doc_data["thumbnail_id"] = str(thumbnail_id)
    return doc


def convert_documents(docs):
    """Convert multiple documents using 'convert_document'.

    Args:
        docs (Iterable[Dict[str, Any]]): Documents that should be converted.

    Returns:
        Iterable[List[Dict[str, Any]]: Yields converted documents. Convert
            result to list or tuple to keep them in memory after first
            iteration.
    """

    for doc in docs:
        yield convert_document(doc)
