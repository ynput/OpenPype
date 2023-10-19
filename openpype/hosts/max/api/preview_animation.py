import os
import logging
import contextlib
from pymxs import runtime as rt
from .lib import get_max_version, render_resolution

log = logging.getLogger("openpype.hosts.max")


@contextlib.contextmanager
def play_preview_when_done(has_autoplay):
    """Function to set preview playback option during
       context

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
    """Function to set viewport camera during context
    ***For 3dsMax 2024+
    Args:
        camera (str): viewport camera for review render
    """
    original = rt.viewport.getCamera()
    has_autoplay = rt.preferences.playPreviewWhenDone
    if not original:
        # if there is no original camera
        # use the current camera as original
        original = rt.getNodeByName(camera)
    review_camera = rt.getNodeByName(camera)
    try:
        rt.viewport.setCamera(review_camera)
        rt.preferences.playPreviewWhenDone = False
        yield
    finally:
        rt.viewport.setCamera(original)
        rt.preferences.playPreviewWhenDone = has_autoplay


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


def publish_review_animation(instance, staging_dir, start,
                             end, ext, fps, viewport_options):
    """Function to set up preview arguments in MaxScript.
    ****For 3dsMax 2024+

    Args:
        instance (str): instance
        filepath (str): output of the preview animation
        start (int): startFrame
        end (int): endFrame
        fps (float): fps value
        viewport_options (dict): viewport setting options

    Returns:
        list: job arguments
    """
    job_args = list()
    filename = "{0}..{1}".format(instance.name, ext)
    filepath = os.path.join(staging_dir, filename)
    filepath = filepath.replace("\\", "/")
    default_option = f'CreatePreview filename:"{filepath}"'
    job_args.append(default_option)
    frame_option = f"outputAVI:false start:{start} end:{end} fps:{fps}" # noqa
    job_args.append(frame_option)

    for key, value in viewport_options.items():
        if isinstance(value, bool):
            if value:
                job_args.append(f"{key}:{value}")

        elif isinstance(value, str):
            if key == "vpStyle":
                if viewport_options[key] == "Realistic":
                    value = "defaultshading"
                elif viewport_options[key] == "Shaded":
                    log.warning(
                        "'Shaded' Mode not supported in "
                        "preview animation in Max 2024..\n"
                        "Using 'defaultshading' instead")
                    value = "defaultshading"
                elif viewport_options[key] == "ConsistentColors":
                    value = "flatcolor"
                else:
                    value = value.lower()
            elif key == "vpPreset":
                if viewport_options[key] == "Quality":
                    value = "highquality"
                elif viewport_options[key] == "Customize":
                    value = "userdefined"
                else:
                    value = value.lower()
            job_args.append(f"{key}: #{value}")

    auto_play_option = "autoPlay:false"
    job_args.append(auto_play_option)

    job_str = " ".join(job_args)
    log.debug(job_str)

    return job_str


def publish_preview_sequences(staging_dir, filename,
                              startFrame, endFrame,
                              percentSize, ext):
    """publish preview animation by creating bitmaps
    ***For 3dsMax Version <2024

    Args:
        staging_dir (str): staging directory
        filename (str): filename
        startFrame (int): start frame
        endFrame (int): end frame
        percentSize (int): percentage of the resolution
        ext (str): image extension
    """
    # get the screenshot
    resolution_percentage = float(percentSize) / 100
    res_width = rt.renderWidth * resolution_percentage
    res_height = rt.renderHeight * resolution_percentage

    viewportRatio = float(res_width / res_height)

    for i in range(startFrame, endFrame + 1):
        rt.sliderTime = i
        fname = "{}.{:04}.{}".format(filename, i, ext)
        filepath = os.path.join(staging_dir, fname)
        filepath = filepath.replace("\\", "/")
        preview_res = rt.bitmap(
            res_width, res_height, filename=filepath)
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

        if rt.keyboard.escPressed:
            rt.exit()
    # clean up the cache
    rt.gc(delayed=True)


def publish_preview_animation(
        instance, staging_dir,
        ext, review_camera,
        startFrame=None, endFrame=None,
        resolution=None,
        viewport_options=None):
    """Render camera review animation

    Args:
        instance (pyblish.api.instance): Instance
        filepath (str): filepath
        review_camera (str): viewport camera for preview render
        startFrame (int): start frame
        endFrame (int): end frame
        viewport_options (dict): viewport setting options
    """

    if startFrame is None:
        startFrame = int(rt.animationRange.start)
    if endFrame is None:
        endFrame = int(rt.animationRange.end)
    if viewport_options is None:
        viewport_options = viewport_options_for_preview_animation()
    if resolution is None:
        resolution = (1920, 1080)
    with play_preview_when_done(False):
        with viewport_camera(review_camera):
            width, height = resolution
            with render_resolution(width, height):
                if int(get_max_version()) < 2024:
                    with viewport_preference_setting(
                            viewport_options["general_viewport"],
                            viewport_options["nitrous_viewport"],
                            viewport_options["vp_btn_mgr"]):
                        percentSize = viewport_options.get("percentSize", 100)

                        publish_preview_sequences(
                            staging_dir, instance.name,
                            startFrame, endFrame, percentSize, ext)
                else:
                    fps = instance.data["fps"]
                    rt.completeRedraw()
                    preview_arg = publish_review_animation(
                        instance, staging_dir,
                        startFrame, endFrame,
                        ext, fps, viewport_options)
                    rt.execute(preview_arg)

    rt.completeRedraw()


def viewport_options_for_preview_animation():
    """
        Function to store the default data of viewport options
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
            "dspSafeFrame":False,
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
