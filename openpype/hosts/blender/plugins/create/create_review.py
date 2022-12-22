"""Create review."""

from openpype.hosts.blender.plugins.create.create_camera import CreateCamera


class CreateReview(CreateCamera):
    """Review is basically a camera with different integration."""

    name = "reviewDefault"
    label = "Review"
    family = "review"
    icon = "video-camera"
