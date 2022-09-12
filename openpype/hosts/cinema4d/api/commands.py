from .lib import WorkfileSettings

def reset_frame_range():
    WorkfileSettings().set_frame_range_handles()

def reset_colorspace():
    print("Not Implemented")

def reset_resolution():
    WorkfileSettings().set_resolution()