import tde4
import os
import subprocess
from openpype.pipeline import KnownPublishError
from openpype.lib.vendor_bin_utils import get_ffmpeg_tool_path, get_ffmpeg_tool_args

def convert_png(input_image):
    new_image_name = input_image.replace("exr", "png")
    ffmpeg_path = get_ffmpeg_tool_path()
    ffmpeg_command = [
        ffmpeg_path,
        '-y',
        '-i', input_image,
        new_image_name,
        "-loglevel",
        "quiet"
    ]

    try:
        subprocess.Popen(ffmpeg_command, shell=True).wait()
        os.remove(input_image)

    except subprocess.CalledProcessError as e:
        raise KnownPublishError("Error during conversion for {0}: {1}".format(input_image, e))


def run_warp4(input_path, output_path):
    warp4_exe_path = "{0}\\bin\\warp4.exe".format(tde4.get3DEInstallPath())
    in_flag = "-in"
    out_flag = "-out"
    action_flag = "-action"
    model_flag = "-model"
    parameters_flag = "-parameters"
    sharpen_flag = "-sharpen"
    overscan_flag = "-overscan"

    command = [
        warp4_exe_path, in_flag, input_path, out_flag, output_path, action_flag, "remove_distortion",
        model_flag, "\"3DE4 Radial, Degree 8\"",
        parameters_flag, "0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000",
        sharpen_flag, "0", overscan_flag, "auto"
    ]

    try:
        subprocess.Popen(command, shell=True).wait()
        return output_path
    except subprocess.CalledProcessError as e:
        raise KnownPublishError("Error during conversion for {0}: {1}".format(input_path, e))
    

def get_distortion_resolution(footage_path):

    first_img = os.listdir(footage_path)[0]
    ffprobe_path = get_ffmpeg_tool_args("ffprobe")[0]
    command = [
        ffprobe_path, "-v", "error", "-show_entries", "stream=width,height", "-of",
        "default=noprint_wrappers=1",
        os.path.join(footage_path, first_img)
    ]

    lines = subprocess.check_output(command, shell=True).decode('utf-8').split('\n')

    # Extract width and height from the lines
    width, height = [int(line.split('=')[1]) for line in lines if line.startswith("width") or line.startswith("height")]
    return (width, height)