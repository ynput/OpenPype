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
def viewport_camera(camera):
    """Set viewport camera during context
    ***For 3dsMax 2024+
    Args:
        camera (str): viewport camera
    """
    original = rt.viewport.getCamera()
    if not original:
        # if there is no original camera
        # use the current camera as original
        original = rt.getNodeByName(camera)
    review_camera = rt.getNodeByName(camera)
    try:
        rt.viewport.setCamera(review_camera)
        yield
    finally:
        rt.viewport.setCamera(original)


@contextlib.contextmanager
def viewport_preference_setting(general_viewport,
                                nitrous_viewport,
                                vp_button_mgr):
    """Function to set viewport setting during context
    ***For Max Version < 2024
    Args:
        camera (str): Viewport camera for review render
        general_viewport (dict): General viewport setting
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
    nitrous_viewport_original = {
        key: getattr(viewport_setting, key) for key in nitrous_viewport
    }

    try:
        rt.viewport.setGridVisibility(1, general_viewport["dspGrid"])
        rt.viewport.EnableSolidBackgroundColorMode(general_viewport["dspBkg"])
        for key, value in vp_button_mgr.items():
            setattr(rt.ViewportButtonMgr, key, value)
        for key, value in nitrous_viewport.items():
            if nitrous_viewport[key] != nitrous_viewport_original[key]:
                setattr(viewport_setting, key, value)
        yield

    finally:
        rt.viewport.setGridVisibility(1, orig_vp_grid)
        rt.viewport.EnableSolidBackgroundColorMode(orig_vp_bkg)
        for key, value in vp_button_mgr_original.items():
            setattr(rt.ViewportButtonMgr, key, value)
        for key, value in nitrous_viewport_original.items():
            setattr(viewport_setting, key, value)


def _render_preview_animation_max_2024(
        filepath, start, end, ext, viewport_options):
    """Render viewport preview with MaxScript using `CreateAnimation`.
    ****For 3dsMax 2024+
    Args:
        filepath (str): filepath for render output without frame number and
            extension, for example: /path/to/file
        start (int): startFrame
        end (int): endFrame
        viewport_options (dict): viewport setting options, e.g.
            {"vpStyle": "defaultshading", "vpPreset": "highquality"}
    Returns:
        list: Created files
    """
    filepath = filepath.replace("\\", "/")
    preview_output = f"{filepath}..{ext}"
    frame_template = f"{filepath}.{{:04d}}.{ext}"
    job_args = list()
    default_option = f'CreatePreview filename:"{preview_output}"'
    job_args.append(default_option)
    frame_option = f"outputAVI:false start:{start} end:{end}"
    job_args.append(frame_option)
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
    auto_play_option = "autoPlay:false"
    job_args.append(auto_play_option)
    job_str = " ".join(job_args)
    log.debug(job_str)
    rt.completeRedraw()
    rt.execute(job_str)
    # Return the created files
    return [frame_template.format(frame) for frame in range(start, end + 1)]


def _render_preview_animation_max_pre_2024(
        filepath, startFrame, endFrame, percentSize, ext):
    """Render viewport animation by creating bitmaps
    ***For 3dsMax Version <2024
    Args:
        filepath (str): filepath without frame numbers and extension
        startFrame (int): start frame
        endFrame (int): end frame
        ext (str): image extension
    Returns:
        list: Created filepaths
    """
    # get the screenshot
    percent = percentSize / 100.0
    res_width = int(round(rt.renderWidth * percent))
    res_height = int(round(rt.renderHeight * percent))
    viewportRatio = float(res_width / res_height)
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
        renderRatio = float(dib_width / dib_height)
        if viewportRatio <= renderRatio:
            heightCrop = (dib_width / renderRatio)
            topEdge = int((dib_height - heightCrop) / 2.0)
            tempImage_bmp = rt.bitmap(dib_width, heightCrop)
            src_box_value = rt.Box2(0, topEdge, dib_width, heightCrop)
        else:
            widthCrop = dib_height * renderRatio
            leftEdge = int((dib_width - widthCrop) / 2.0)
            tempImage_bmp = rt.bitmap(widthCrop, dib_height)
            src_box_value = rt.Box2(0, leftEdge, dib_width, dib_height)
        rt.pasteBitmap(dib, tempImage_bmp, src_box_value, rt.Point2(0, 0))
        # copy the bitmap and close it
        rt.copy(tempImage_bmp, preview_res)
        rt.close(tempImage_bmp)
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
        with viewport_camera(camera):
            with render_resolution(width, height):
                if int(get_max_version()) < 2024:
                    with viewport_preference_setting(
                            viewport_options["general_viewport"],
                            viewport_options["nitrous_viewport"],
                            viewport_options["vp_btn_mgr"]
                    ):
                        percentSize = viewport_options.get("percentSize", 100)
                        return _render_preview_animation_max_pre_2024(
                            filepath,
                            start_frame,
                            end_frame,
                            percentSize,
                            ext
                        )
                else:
                    return _render_preview_animation_max_2024(
                        filepath,
                        start_frame,
                        end_frame,
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
            "percentSize": 100,
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
        viewport_options.update({"percentSize": 100})
        general_viewport = {
            "dspBkg": True,
            "dspGrid": False
        }
        nitrous_viewport = {
            "VisualStyleMode": "defaultshading",
            "ViewportPreset": "highquality",
            "UseTextureEnabled": False
        }
        viewport_options["general_viewport"] = general_viewport
        viewport_options["nitrous_viewport"] = nitrous_viewport
        viewport_options["vp_btn_mgr"] = {
            "EnableButtons": False}
        return viewport_options
