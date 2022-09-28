# --- Folders ---
FOLDER_ATTRIBS = {
    "clipIn",
    "clipOut",
    "fps",
    "frameEnd",
    "handleEnd",
    "frameStart",
    "handleStart",
    "pixelAspect",
    "resolutionHeight",
    "resolutionWidth",
}
FOLDER_ATTRIBS_FIELDS = {
    "attrib.{}".format(attr)
    for attr in FOLDER_ATTRIBS
}
# V3 has tasks vs. V4 which does not have
DEFAULT_V3_FOLDER_FIELDS = {
    "id",
    "name",
    "path",
    "parentId",
    "tasks",
    "active",
    "parents",
    "thumbnailId"
} | FOLDER_ATTRIBS_FIELDS
DEFAULT_FOLDER_FIELDS = {
    "id",
    "name",
    "path",
    "parentId",
    "active",
    "parents",
    "thumbnailId"
} | FOLDER_ATTRIBS_FIELDS

# --- Tasks ---
TASK_ATTRIBS = {
    "clipIn",
    "clipOut",
    "fps",
    "frameStart",
    "frameEnd",
    "handleEnd",
    "handleStart",
    "newAttribute",
    "pixelAspect",
    "resolutionHeight",
    "resolutionWidth",
}
TASK_ATTRIBS_FIELDS = {
    "attrib.{}".format(attr)
    for attr in TASK_ATTRIBS
}
DEFAULT_TASK_FIELDS = {
    "id",
    "name",
    "taskType",
    "assignees",
} | TASK_ATTRIBS_FIELDS

# --- Subsets ---
SUBSET_ATTRIBS = {
    "subsetGroup",
}
SUBSET_ATTRIBS_FIELDS = {
    "attrib.{}".format(attr)
    for attr in SUBSET_ATTRIBS
}
DEFAULT_SUBSET_FIELDS = {
    "id",
    "name",
    "active",
    "family",
    "folderId",
} | SUBSET_ATTRIBS_FIELDS

# --- Versions ---
VERSION_ATTRIBS = {
    "fps",
    "resolutionWidth",
    "resolutionHeight",
    "pixelAspect",
    "clipIn",
    "clipOut",
    "families",
    "frameStart",
    "frameEnd",
    "handleStart",
    "handleEnd",
    "intent",
    "source",
    "comment",
    "machine",
    "colorSpace",
}
VERSION_ATTRIBS_FIELDS = {
    "attrib.{}".format(attr)
    for attr in VERSION_ATTRIBS
}
DEFAULT_VERSION_FIELDS = {
    "id",
    "name",
    "version",
    "active",
    "subsetId",
    "taskId",
    "author",
    "thumbnailId",
    "createdAt",
    "updatedAt",
} | VERSION_ATTRIBS_FIELDS

# --- Representations ---
REPRESENTATION_ATTRIBS = {
    "clipIn",
    "clipOut",
    "extension",
    "fps",
    "frameEnd",
    "frameStart",
    "handleEnd",
    "handleStart",
    "pixelAspect",
    "resolutionHeight",
    "resolutionWidth",
    "path",
    "template",
}
REPRESENTATION_ATTRIBS_FIELDS = {
    "attrib.{}".format(attr)
    for attr in REPRESENTATION_ATTRIBS
}
REPRESENTATION_FILES_FIELDS = {
    "files.baseName",
    "files.hash",
    "files.id",
    "files.path",
    "files.size",
}
DEFAULT_REPRESENTATION_FIELDS = {
    "id",
    "name",
    "context",
    "createdAt",
    "active",
    "versionId",
} | REPRESENTATION_ATTRIBS_FIELDS | REPRESENTATION_FILES_FIELDS
