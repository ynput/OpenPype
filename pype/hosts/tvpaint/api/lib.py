from PIL import Image


def composite_images(
    input_image_paths, output_filepath, scene_width, scene_height
):
    img_obj = None
    for image_filepath in input_image_paths:
        _img_obj = Image.open(image_filepath)
        if img_obj is None:
            img_obj = _img_obj
        else:
            img_obj.alpha_composite(_img_obj)

    if img_obj is None:
        img_obj = Image.new("RGBA", (scene_width, scene_height), (0, 0, 0, 0))
    img_obj.save(output_filepath)
