import pyblish.api


ValidatePipelineOrder = pyblish.api.ValidatorOrder + 0.05
ValidateContentsOrder = pyblish.api.ValidatorOrder + 0.1
ValidateSceneOrder = pyblish.api.ValidatorOrder + 0.2
ValidateMeshOrder = pyblish.api.ValidatorOrder + 0.3

DEFAULT_PUBLISH_TEMPLATE = "publish"
DEFAULT_HERO_PUBLISH_TEMPLATE = "hero"
TRANSIENT_DIR_TEMPLATE = "transient"
