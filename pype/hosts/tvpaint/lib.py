from PIL import Image


def composite_images(input_image_paths, output_filepath):
    """Composite images in order from passed list.

    Raises:
        ValueError: When entered list is empty.
    """
    if not input_image_paths:
        raise ValueError("Nothing to composite.")

    img_obj = None
    for image_filepath in input_image_paths:
        _img_obj = Image.open(image_filepath)
        if img_obj is None:
            img_obj = _img_obj
        else:
            img_obj.alpha_composite(_img_obj)
    img_obj.save(output_filepath)
