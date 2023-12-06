# Environments where server url and api key are stored for global connection
SERVER_URL_ENV_KEY = "AYON_SERVER_URL"
SERVER_API_ENV_KEY = "AYON_API_KEY"
SERVER_TIMEOUT_ENV_KEY = "AYON_SERVER_TIMEOUT"
SERVER_RETRIES_ENV_KEY = "AYON_SERVER_RETRIES"
# Default variant used for settings
DEFAULT_VARIANT_ENV_KEY = "AYON_DEFAULT_SETTINGS_VARIANT"
# Default site id used for connection
SITE_ID_ENV_KEY = "AYON_SITE_ID"

# Backwards compatibility
SERVER_TOKEN_ENV_KEY = SERVER_API_ENV_KEY

# --- User ---
DEFAULT_USER_FIELDS = {
    "accessGroups",
    "defaultAccessGroups",
    "name",
    "isService",
    "isManager",
    "isGuest",
    "isAdmin",
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
    "data",
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
    "data",
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
    "data",
}

# --- Products ---
DEFAULT_PRODUCT_FIELDS = {
    "id",
    "name",
    "folderId",
    "active",
    "productType",
    "data",
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
    "data",
}

# --- Representations ---
DEFAULT_REPRESENTATION_FIELDS = {
    "id",
    "name",
    "context",
    "createdAt",
    "active",
    "versionId",
    "data",
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
    "data",
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
