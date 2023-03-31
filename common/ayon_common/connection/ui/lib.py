def set_style_property(widget, property_name, property_value):
    """Set widget's property that may affect style.

    Style of widget is polished if current property value is different.
    """

    cur_value = widget.property(property_name)
    if cur_value == property_value:
        return
    widget.setProperty(property_name, property_value)
    widget.style().polish(widget)
