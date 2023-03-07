# --- Project ---
DEFAULT_PROJECT_FIELDS = {
    "active",
    "name",
    "code",
    "config",
    "data",
    "createdAt",
}

# --- Folders ---
DEFAULT_FOLDER_FIELDS = {
    "id",
    "name",
    "path",
    "parentId",
    "active",
    "parents",
    "thumbnailId"
}

# --- Tasks ---
DEFAULT_TASK_FIELDS = {
    "id",
    "name",
    "taskType",
    "assignees",
}

# --- Subsets ---
DEFAULT_SUBSET_FIELDS = {
    "id",
    "name",
    "active",
    "family",
    "folderId",
}

# --- Versions ---
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
}

# --- Representations ---
DEFAULT_REPRESENTATION_FIELDS = {
    "id",
    "name",
    "context",
    "createdAt",
    "active",
    "versionId",
}

REPRESENTATION_FILES_FIELDS = {
    "files.name",
    "files.hash",
    "files.id",
    "files.path",
    "files.size",
}

DEFAULT_WORKFILE_INFO_FIELDS = {
    "active",
    "createdAt",
    "createdBy",
    "id",
    "name",
    "path",
    "projectName",
    "taskId",
    "thumbnailId",
    "updatedAt",
    "updatedBy",
}
