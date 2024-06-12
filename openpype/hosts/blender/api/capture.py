
"""Blender Capture
Playblasting with independent viewport, camera and display options
"""
import contextlib
import bpy

from .lib import maintained_time
from .plugin import deselect_all, create_blender_context


def capture(
    camera=None,
    width=None,
    height=None,
    filename=None,
    start_frame=None,
    end_frame=None,
    step_frame=None,
    sound=None,
    isolate=None,
    maintain_aspect_ratio=True,
    overwrite=False,
    image_settings=None,
    display_options=None
):
    """Playblast in an independent windows
    Arguments:
        camera (str, optional): Name of camera, defaults to "Camera"
        width (int, optional): Width of output in pixels
        height (int, optional): Height of output in pixels
        filename (str, optional): Name of output file path. Defaults to current
            render output path.
        start_frame (int, optional): Defaults to current start frame.
        end_frame (int, optional): Defaults to current end frame.
        step_frame (int, optional): Defaults to 1.
        sound (str, optional):  Specify the sound node to be used during
            playblast. When None (default) no sound will be used.
        isolate (list): List of nodes to isolate upon capturing
        maintain_aspect_ratio (bool, optional): Modify height in order to
            maintain aspect ratio.
        overwrite (bool, optional): Whether or not to overwrite if file
            already exists. If disabled and file exists and error will be
            raised.
        image_settings (dict, optional): Supplied image settings for render,
            using `ImageSettings`
        display_options (dict, optional): Supplied display options for render
    """

    scene = bpy.context.scene
    camera = camera or "Camera"

    # Ensure camera exists.
    if camera not in scene.objects and camera != "AUTO":
        raise RuntimeError("Camera does not exist: {0}".format(camera))

    # Ensure resolution.
    if width and height:
        maintain_aspect_ratio = False
    width = width or scene.render.resolution_x
    height = height or scene.render.resolution_y
    if maintain_aspect_ratio:
        ratio = scene.render.resolution_x / scene.render.resolution_y
        height = round(width / ratio)

    # Get frame range.
    if start_frame is None:
        start_frame = scene.frame_start
    if end_frame is None:
        end_frame = scene.frame_end
    if step_frame is None:
        step_frame = 1
    frame_range = (start_frame, end_frame, step_frame)

    if filename is None:
        filename = scene.render.filepath

    render_options = {
        "filepath": "{}.".format(filename.rstrip(".")),
        "resolution_x": width,
        "resolution_y": height,
        "use_overwrite": overwrite,
    }

    with _independent_window() as window:

        applied_view(window, camera, isolate, options=display_options)

        with contextlib.ExitStack() as stack:
            stack.enter_context(maintain_camera(window, camera))
            stack.enter_context(applied_frame_range(window, *frame_range))
            stack.enter_context(applied_render_options(window, render_options))
            stack.enter_context(applied_image_settings(window, image_settings))
            stack.enter_context(maintained_time())

            bpy.ops.render.opengl(
                animation=True,
                render_keyed_only=False,
                sequencer=False,
                write_still=False,
                view_context=True
            )

    return filename


ImageSettings = {
    "file_format": "FFMPEG",
    "color_mode": "RGB",
    "ffmpeg": {
        "format": "QUICKTIME",
        "use_autosplit": False,
        "codec": "H264",
        "constant_rate_factor": "MEDIUM",
        "gopsize": 18,
        "use_max_b_frames": False,
    },
}


def isolate_objects(window, objects):
    """Isolate selection"""
    deselect_all()

    for obj in objects:
        obj.select_set(True)

    context = create_blender_context(selected=objects, window=window)

    with bpy.context.temp_override(**context):
        bpy.ops.view3d.view_axis(type="FRONT")
        bpy.ops.view3d.localview()

    deselect_all()


def _apply_options(entity, options):
    for option, value in options.items():
        if isinstance(value, dict):
            _apply_options(getattr(entity, option), value)
        else:
            setattr(entity, option, value)


def applied_view(window, camera, isolate=None, options=None):
    """Apply view options to window."""
    area = window.screen.areas[0]
    space = area.spaces[0]

    area.ui_type = "VIEW_3D"

    types = {"MESH", "GPENCIL"}
    objects = [obj for obj in window.scene.objects if obj.type in types]

    if camera == "AUTO":
        space.region_3d.view_perspective = "ORTHO"
        isolate_objects(window, isolate or objects)
    else:
        isolate_objects(window, isolate or objects)
        space.camera = window.scene.objects.get(camera)
        space.region_3d.view_perspective = "CAMERA"

    if isinstance(options, dict):
        _apply_options(space, options)
    else:
        space.shading.type = "SOLID"
        space.shading.color_type = "MATERIAL"
        space.show_gizmo = False
        space.overlay.show_overlays = False


@contextlib.contextmanager
def applied_frame_range(window, start, end, step):
    """Context manager for setting frame range."""
    # Store current frame range
    current_frame_start = window.scene.frame_start
    current_frame_end = window.scene.frame_end
    current_frame_step = window.scene.frame_step
    # Apply frame range
    window.scene.frame_start = start
    window.scene.frame_end = end
    window.scene.frame_step = step
    try:
        yield
    finally:
        # Restore frame range
        window.scene.frame_start = current_frame_start
        window.scene.frame_end = current_frame_end
        window.scene.frame_step = current_frame_step


@contextlib.contextmanager
def applied_render_options(window, options):
    """Context manager for setting render options."""
    render = window.scene.render

    # Store current settings
    original = {}
    for opt in options.copy():
        try:
            original[opt] = getattr(render, opt)
        except ValueError:
            options.pop(opt)

    # Apply settings
    _apply_options(render, options)

    try:
        yield
    finally:
        # Restore previous settings
        _apply_options(render, original)


@contextlib.contextmanager
def applied_image_settings(window, options):
    """Context manager to override image settings."""

    options = options or ImageSettings.copy()
    ffmpeg = options.pop("ffmpeg", {})
    render = window.scene.render

    # Store current image settings
    original = {}
    for opt in options.copy():
        try:
            original[opt] = getattr(render.image_settings, opt)
        except ValueError:
            options.pop(opt)

    # Store current ffmpeg settings
    original_ffmpeg = {}
    for opt in ffmpeg.copy():
        try:
            original_ffmpeg[opt] = getattr(render.ffmpeg, opt)
        except ValueError:
            ffmpeg.pop(opt)

    # Apply image settings
    for opt, value in options.items():
        setattr(render.image_settings, opt, value)

    # Apply ffmpeg settings
    for opt, value in ffmpeg.items():
        setattr(render.ffmpeg, opt, value)

    try:
        yield
    finally:
        # Restore previous settings
        for opt, value in original.items():
            setattr(render.image_settings, opt, value)
        for opt, value in original_ffmpeg.items():
            setattr(render.ffmpeg, opt, value)


@contextlib.contextmanager
def maintain_camera(window, camera):
    """Context manager to override camera."""
    current_camera = window.scene.camera
    if camera in window.scene.objects:
        window.scene.camera = window.scene.objects.get(camera)
    try:
        yield
    finally:
        window.scene.camera = current_camera


@contextlib.contextmanager
def _independent_window():
    """Create capture-window context."""
    context = create_blender_context()
    current_windows = set(bpy.context.window_manager.windows)
    with bpy.context.temp_override(**context):
        bpy.ops.wm.window_new()
        window = list(
            set(bpy.context.window_manager.windows) - current_windows)[0]
        context["window"] = window
        try:
            yield window
        finally:
            bpy.ops.wm.window_close()
