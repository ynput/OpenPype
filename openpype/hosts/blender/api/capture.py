"""Blender Capture

Playblasting with independent viewport, camera and display options

"""
import contextlib
import bpy

from .lib import maintained_time, maintained_selection, maintained_visibility
from .plugin import deselect_all, context_override


def capture(
    camera=None,
    width=None,
    height=None,
    filepath=None,
    isolate=None,
    focus=None,
    maintain_aspect_ratio=True,
    overwrite=False,
    display_options=None,
    **preset_settings,
):
    """Playblast in an independent windows
    Arguments:
        camera (str, optional): Name of the camera.
            Defaults to current scene camera.
        width (int, optional): Width of output in pixels
        height (int, optional): Height of output in pixels
        filepath (str, optional): Name of output file path. Defaults to current
            render output path.
        isolate (list, optional): List of nodes to isolate upon capturing
        maintain_aspect_ratio (bool, optional): Modify height in order to
            maintain aspect ratio.
        overwrite (bool, optional): Whether or not to overwrite if file
            already exists. If disabled and file exists and error will be
            raised. Default to False.
        display_options (dict, optional): Supplied display options for render
        **preset_settings: Arbitrary keyword arguments for scene and render
            settings overrides.

    Returns:
        str: The output file path.
    """

    scene = bpy.context.scene
    if not camera and scene.camera:
        camera = scene.camera.name

    # Ensure camera exists.
    if camera not in scene.objects and camera != "AUTO":
        raise RuntimeError(f"Camera does not exist: {camera}")

    # Ensure resolution.
    if width and height:
        maintain_aspect_ratio = False
    width = width or scene.render.resolution_x
    height = height or scene.render.resolution_y
    if maintain_aspect_ratio:
        ratio = scene.render.resolution_x / scene.render.resolution_y
        height = round(width / ratio)

    # Get filepath.
    if filepath is None:
        filepath = scene.render.filepath

    # Get frame range.
    preset_settings.setdefault("frame_start", scene.frame_start)
    preset_settings.setdefault("frame_end", scene.frame_end)
    preset_settings.setdefault("frame_step", scene.frame_step)

    # Get render settings.
    preset_settings.setdefault("render", {})
    preset_settings["render"].update(
        {
            "filepath": f"{filepath.rstrip('.')}.",
            "resolution_x": width,
            "resolution_y": height,
            "use_overwrite": overwrite,
        }
    )

    # Move image_settings into render options.
    # NOTE: That fix deprecated image_settings argument.
    preset_settings["render"].setdefault(
        "image_settings", preset_settings.get("image_settings", {})
    )

    with contextlib.ExitStack() as stack:
        stack.enter_context(maintained_time())
        stack.enter_context(maintained_selection())
        stack.enter_context(maintained_visibility())
        window = stack.enter_context(_independent_window())

        applied_view(window, camera, isolate, focus, options=display_options)

        stack.enter_context(applied_camera(window, camera))
        stack.enter_context(applied_preset_settings(window, preset_settings))

        with context_override(window=window):
            bpy.ops.render.opengl(
                animation=True,
                render_keyed_only=False,
                sequencer=False,
                write_still=False,
                view_context=True,
            )

    return filepath


def isolate_objects(window, objects, focus=None):
    """Isolate selected objects and set focus on this one or given objects list
    in optional argument.
    
    Arguments:
        window (bpy.types.Window): The Blender active window. 
        objects (list, optional): List of objects to be isolate in viewport.
        focus (list, optional): List of objects used for focus view.
    """

    # Hide all scene objects excepte given object liste to be isolate.
    for obj in bpy.context.scene.objects:
        try:
            obj.hide_set(obj not in objects)
        except RuntimeError:
            continue

    # Select objects to center the view in front axis.
    deselect_all()
    focus = focus or objects
    for obj in focus:
        try:
            obj.select_set(True)
        except RuntimeError:
            continue
    with context_override(selected=focus, window=window):
        bpy.ops.view3d.view_axis(type="FRONT")
        bpy.ops.view3d.view_selected(use_all_regions=False)
    deselect_all()


def _apply_settings(entity, settings):
    """Apply settings for given entity.
    
    Arguments:
        entity (bpy.types.bpy_struct): The entity.
        settings (dict): Dict of settings.
    """
    for option, value in settings.items():
        if hasattr(entity, option):
            if isinstance(value, dict):
                _apply_settings(getattr(entity, option), value)
            else:
                setattr(entity, option, value)


def _get_current_settings(entity, settings):
    """Get current settings for given entity.

    Arguments:
        entity (bpy.types.bpy_struct): The entity.
        settings (dict): Dict of settings.
        
    Returns:
        dict: The current settings for the entity.
    """
    current_settings = {}
    for option in settings:
        if hasattr(entity, option):
            if isinstance(settings[option], dict):
                current_settings[option] = _get_current_settings(
                    getattr(entity, option), settings[option]
                )
            else:
                current_settings[option] = getattr(entity, option)

    return current_settings


def applied_view(window, camera, isolate=None, focus=None, options=None):
    """Apply view options to window.
    
    Arguments:
        window (bpy.types.Window): The Blender active window.
        camera (str): The camera name to set as active camera.
            Use AUTO as special value to use centered orthographic view.
        isolate (list, optional): List of objects to be isolate in viewport.
        focus (list, optional): List of objects used for focus view
            if argument camera is AUTO.
        options (dict, optional): The display options.
    """
    # Change area of window to 3D view
    area = window.screen.areas[0]
    area.ui_type = "VIEW_3D"
    space = area.spaces[0]

    visible = [obj for obj in window.scene.objects if obj.visible_get()]

    if camera == "AUTO":
        space.region_3d.view_perspective = "ORTHO"
        isolate_objects(window, isolate or visible, focus)
    else:
        isolate_objects(window, isolate or visible, focus)
        space.camera = window.scene.objects.get(camera)
        space.region_3d.view_perspective = "CAMERA"

    if isinstance(options, dict):
        _apply_settings(space, options)
    else:
        space.shading.type = "SOLID"
        space.shading.color_type = "MATERIAL"
        space.show_gizmo = False
        space.overlay.show_overlays = False


@contextlib.contextmanager
def applied_preset_settings(window, settings):
    """Context manager to override Blender settings.
    
    Arguments:
        window (bpy.types.Window): The Blender active window.
        settings (dict): The settings to apply.
    """

    # Store current settings
    old_settings = _get_current_settings(window.scene, settings)

    # Apply settings
    _apply_settings(window.scene, settings)

    try:
        yield
    finally:
        # Restore previous settings
        _apply_settings(window.scene, old_settings)


@contextlib.contextmanager
def applied_camera(window, camera):
    """Context manager to override camera.
    
    Arguments:
        window (bpy.types.Window): The Blender active window.
        camera (str): The camera name to set as active camera.
    """
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
    current_windows = set(bpy.context.window_manager.windows)
    with context_override():
        bpy.ops.wm.window_new()
    window = list(set(bpy.context.window_manager.windows) - current_windows)[0]
    try:
        yield window
    finally:
        with context_override(window=window):
            bpy.ops.wm.window_close()
