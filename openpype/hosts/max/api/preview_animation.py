import logging
import contextlib
from pymxs import runtime as rt
from .lib import get_max_version, render_resolution

log = logging.getLogger("openpype.hosts.max")


@contextlib.contextmanager
def play_preview_when_done(has_autoplay):
    """Set preview playback option during context

    Args:
        has_autoplay (bool): autoplay during creating
            preview animation
    """
    current_playback = rt.preferences.playPreviewWhenDone
    try:
        rt.preferences.playPreviewWhenDone = has_autoplay
        yield
    finally:
        rt.preferences.playPreviewWhenDone = current_playback


@contextlib.contextmanager
def viewport_layout_and_camera(camera, layout="layout_1"):
    """Set viewport layout and camera during context
    ***For 3dsMax 2024+
    Args:
        camera (str): viewport camera
        layout (str): layout to use in viewport, defaults to `layout_1`
            Use None to not change viewport layout during context.
    """
    original_camera = rt.viewport.getCamera()
    original_layout = rt.viewport.getLayout()
    if not original_camera:
        # if there is no original camera
        # use the current camera as original
        original_camera = rt.getNodeByName(camera)
    review_camera = rt.getNodeByName(camera)
    try:
        if layout is not None:
            layout = rt.Name(layout)
            if rt.viewport.getLayout() != layout:
                rt.viewport.setLayout(layout)
        rt.viewport.setCamera(review_camera)
        yield
    finally:
        rt.viewport.setLayout(original_layout)
        rt.viewport.setCamera(original_camera)


@contextlib.contextmanager
def viewport_preference_setting(general_viewport,
                                nitrous_manager,
                                nitrous_viewport,
                                vp_button_mgr):
    """Function to set viewport setting during context
    ***For Max Version < 2024
    Args:
        camera (str): Viewport camera for review render
        general_viewport (dict): General viewport setting
        nitrous_manager (dict): Nitrous graphic manager
        nitrous_viewport (dict): Nitrous setting for
            preview animation
        vp_button_mgr (dict): Viewport button manager Setting
        preview_preferences (dict): Preview Preferences Setting
    """
    orig_vp_grid = rt.viewport.getGridVisibility(1)
    orig_vp_bkg = rt.viewport.IsSolidBackgroundColorMode()

    nitrousGraphicMgr = rt.NitrousGraphicsManager
    viewport_setting = nitrousGraphicMgr.GetActiveViewportSetting()
    vp_button_mgr_original = {
        key: getattr(rt.ViewportButtonMgr, key) for key in vp_button_mgr
    }
    nitrous_manager_original = {
        key: getattr(nitrousGraphicMgr, key) for key in nitrous_manager
    }
    nitrous_viewport_original = {
        key: getattr(viewport_setting, key) for key in nitrous_viewport
    }

    try:
        rt.viewport.setGridVisibility(1, general_viewport["dspGrid"])
        rt.viewport.EnableSolidBackgroundColorMode(general_viewport["dspBkg"])
        for key, value in vp_button_mgr.items():
            setattr(rt.ViewportButtonMgr, key, value)
        for key, value in nitrous_manager.items():
            setattr(nitrousGraphicMgr, key, value)
        for key, value in nitrous_viewport.items():
            if nitrous_viewport[key] != nitrous_viewport_original[key]:
                setattr(viewport_setting, key, value)
        yield

    finally:
        rt.viewport.setGridVisibility(1, orig_vp_grid)
        rt.viewport.EnableSolidBackgroundColorMode(orig_vp_bkg)
        for key, value in vp_button_mgr_original.items():
            setattr(rt.ViewportButtonMgr, key, value)
        for key, value in nitrous_manager_original.items():
            setattr(nitrousGraphicMgr, key, value)
        for key, value in nitrous_viewport_original.items():
            setattr(viewport_setting, key, value)


def _render_preview_animation_max_2024(
        filepath, start, end, percentSize, ext, viewport_options):
    """Render viewport preview with MaxScript using `CreateAnimation`.
    ****For 3dsMax 2024+
    Args:
        filepath (str): filepath for render output without frame number and
            extension, for example: /path/to/file
        start (int): startFrame
        end (int): endFrame
        percentSize (float): render resolution multiplier by 100
            e.g. 100.0 is 1x, 50.0 is 0.5x, 150.0 is 1.5x
        viewport_options (dict): viewport setting options, e.g.
            {"vpStyle": "defaultshading", "vpPreset": "highquality"}
    Returns:
        list: Created files
    """
    # the percentSize argument must be integer
    percent = int(percentSize)
    filepath = filepath.replace("\\", "/")
    preview_output = f"{filepath}..{ext}"
    frame_template = f"{filepath}.{{:04d}}.{ext}"
    job_args = []
    for key, value in viewport_options.items():
        if isinstance(value, bool):
            if value:
                job_args.append(f"{key}:{value}")
        elif isinstance(value, str):
            if key == "vpStyle":
                if value == "Realistic":
                    value = "defaultshading"
                elif value == "Shaded":
                    log.warning(
                        "'Shaded' Mode not supported in "
                        "preview animation in Max 2024.\n"
                        "Using 'defaultshading' instead.")
                    value = "defaultshading"
                elif value == "ConsistentColors":
                    value = "flatcolor"
                else:
                    value = value.lower()
            elif key == "vpPreset":
                if value == "Quality":
                    value = "highquality"
                elif value == "Customize":
                    value = "userdefined"
                else:
                    value = value.lower()
            job_args.append(f"{key}: #{value}")

    job_str = (
        f'CreatePreview filename:"{preview_output}" outputAVI:false '
        f"percentSize:{percent} start:{start} end:{end} "
        f"{' '.join(job_args)} "
        "autoPlay:false"
    )
    rt.completeRedraw()
    rt.execute(job_str)
    # Return the created files
    return [frame_template.format(frame) for frame in range(start, end + 1)]


def _render_preview_animation_max_pre_2024(
        filepath, startFrame, endFrame,
        width, height, percentSize, ext):
    """Render viewport animation by creating bitmaps
    ***For 3dsMax Version <2024
    Args:
        filepath (str): filepath without frame numbers and extension
        startFrame (int): start frame
        endFrame (int): end frame
        width (int): render resolution width
        height (int): render resolution height
        percentSize (float): render resolution multiplier by 100
            e.g. 100.0 is 1x, 50.0 is 0.5x, 150.0 is 1.5x
        ext (str): image extension
    Returns:
        list: Created filepaths
    """

    # get the screenshot
    percent = percentSize / 100.0
    res_width = width * percent
    res_height = height * percent
    frame_template = "{}.{{:04}}.{}".format(filepath, ext)
    frame_template.replace("\\", "/")
    files = []
    user_cancelled = False
    for frame in range(startFrame, endFrame + 1):
        rt.sliderTime = frame
        filepath = frame_template.format(frame)
        preview_res = rt.bitmap(
            res_width, res_height, filename=filepath
        )
        dib = rt.gw.getViewportDib()
        dib_width = float(dib.width)
        dib_height = float(dib.height)
        # aspect ratio
        viewportRatio = dib_width / dib_height
        renderRatio = float(res_width / res_height)
        if viewportRatio < renderRatio:
            heightCrop = (dib_width / renderRatio)
            topEdge = int((dib_height - heightCrop) / 2.0)
            tempImage_bmp = rt.bitmap(dib_width, heightCrop)
            src_box_value = rt.Box2(0, topEdge, dib_width, heightCrop)
            rt.pasteBitmap(dib, tempImage_bmp, src_box_value, rt.Point2(0, 0))
            rt.copy(tempImage_bmp, preview_res)
            rt.close(tempImage_bmp)
        elif viewportRatio > renderRatio:
            widthCrop = dib_height * renderRatio
            leftEdge = int((dib_width - widthCrop) / 2.0)
            tempImage_bmp = rt.bitmap(widthCrop, dib_height)
            src_box_value = rt.Box2(leftEdge, 0, widthCrop, dib_height)
            rt.pasteBitmap(dib, tempImage_bmp, src_box_value, rt.Point2(0, 0))
            rt.copy(tempImage_bmp, preview_res)
            rt.close(tempImage_bmp)
        else:
            rt.copy(dib, preview_res)
        rt.save(preview_res)
        rt.close(preview_res)
        rt.close(dib)
        files.append(filepath)
        if rt.keyboard.escPressed:
            user_cancelled = True
            break
    # clean up the cache
    rt.gc(delayed=True)
    if user_cancelled:
        raise RuntimeError("User cancelled rendering of viewport animation.")
    return files


def render_preview_animation(
        filepath,
        ext,
        camera,
        start_frame=None,
        end_frame=None,
        percentSize=100.0,
        width=1920,
        height=1080,
        viewport_options=None):
    """Render camera review animation
    Args:
        filepath (str): filepath to render to, without frame number and
            extension
        ext (str): output file extension
        camera (str): viewport camera for preview render
        start_frame (int): start frame
        end_frame (int): end frame
        percentSize (float): render resolution multiplier by 100
            e.g. 100.0 is 1x, 50.0 is 0.5x, 150.0 is 1.5x
        width (int): render resolution width
        height (int): render resolution height
        viewport_options (dict): viewport setting options
    Returns:
        list: Rendered output files
    """
    if start_frame is None:
        start_frame = int(rt.animationRange.start)
    if end_frame is None:
        end_frame = int(rt.animationRange.end)

    if viewport_options is None:
        viewport_options = viewport_options_for_preview_animation()
    with play_preview_when_done(False):
        with viewport_layout_and_camera(camera):
            if int(get_max_version()) < 2024:
                with viewport_preference_setting(
                        viewport_options["general_viewport"],
                        viewport_options["nitrous_manager"],
                        viewport_options["nitrous_viewport"],
                        viewport_options["vp_btn_mgr"]
                ):
                    return _render_preview_animation_max_pre_2024(
                        filepath,
                        start_frame,
                        end_frame,
                        width,
                        height,
                        percentSize,
                        ext
                    )
            else:
                with render_resolution(width, height):
                    return _render_preview_animation_max_2024(
                        filepath,
                        start_frame,
                        end_frame,
                        percentSize,
                        ext,
                        viewport_options
                    )


def viewport_options_for_preview_animation():
    """Get default viewport options for `render_preview_animation`.

    Returns:
        dict: viewport setting options
    """
    # viewport_options should be the dictionary
    if int(get_max_version()) < 2024:
        return {
            "visualStyleMode": "defaultshading",
            "viewportPreset": "highquality",
            "vpTexture": False,
            "dspGeometry": True,
            "dspShapes": False,
            "dspLights": False,
            "dspCameras": False,
            "dspHelpers": False,
            "dspParticles": True,
            "dspBones": False,
            "dspBkg": True,
            "dspGrid": False,
            "dspSafeFrame": False,
            "dspFrameNums": False
        }
    else:
        viewport_options = {}
        viewport_options["general_viewport"] = {
            "dspBkg": True,
            "dspGrid": False
        }
        viewport_options["nitrous_manager"] = {
            "AntialiasingQuality": "None"
        }
        viewport_options["nitrous_viewport"] = {
            "VisualStyleMode": "defaultshading",
            "ViewportPreset": "highquality",
            "UseTextureEnabled": False
        }
        viewport_options["vp_btn_mgr"] = {
            "EnableButtons": False}
        return viewport_options
