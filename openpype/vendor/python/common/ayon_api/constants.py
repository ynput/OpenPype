# Environments where server url and api key are stored for global connection
SERVER_URL_ENV_KEY = "AYON_SERVER_URL"
SERVER_API_ENV_KEY = "AYON_API_KEY"
# Backwards compatibility
SERVER_TOKEN_ENV_KEY = SERVER_API_ENV_KEY

# --- User ---
DEFAULT_USER_FIELDS = {
    "roles",
    "name",
    "isService",
    "isManager",
    "isGuest",
    "isAdmin",
    "defaultRoles",
    "createdAt",
    "active",
    "hasPassword",
    "updatedAt",
    "apiKeyPreview",
    "attrib.avatarUrl",
    "attrib.email",
    "attrib.fullName",
}

# --- Product types ---
DEFAULT_PRODUCT_TYPE_FIELDS = {
    "name",
    "icon",
    "color",
}

# --- Project ---
DEFAULT_PROJECT_FIELDS = {
    "active",
    "name",
    "code",
    "config",
    "createdAt",
}

# --- Folders ---
DEFAULT_FOLDER_FIELDS = {
    "id",
    "name",
    "label",
    "folderType",
    "path",
    "parentId",
    "active",
    "thumbnailId",
}

# --- Tasks ---
DEFAULT_TASK_FIELDS = {
    "id",
    "name",
    "label",
    "taskType",
    "folderId",
    "active",
    "assignees",
}

# --- Products ---
DEFAULT_PRODUCT_FIELDS = {
    "id",
    "name",
    "folderId",
    "active",
    "productType",
}

# --- Versions ---
DEFAULT_VERSION_FIELDS = {
    "id",
    "name",
    "version",
    "productId",
    "taskId",
    "active",
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

# --- Workfile info ---
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

DEFAULT_EVENT_FIELDS = {
    "id",
    "hash",
    "createdAt",
    "dependsOn",
    "description",
    "project",
    "retries",
    "sender",
    "status",
    "topic",
    "updatedAt",
    "user",
}
