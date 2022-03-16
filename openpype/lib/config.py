# -*- coding: utf-8 -*-
"""Get configuration data."""
import datetime


def get_datetime_data(datetime_obj=None):
    """Returns current datetime data as dictionary.

    Args:
        datetime_obj (datetime): Specific datetime object

    Returns:
        dict: prepared date & time data

    Available keys:
        "d" - <Day of month number> in shortest possible way.
        "dd" - <Day of month number> with 2 digits.
        "ddd" - <Week day name> shortened week day. e.g.: `Mon`, ...
        "dddd" - <Week day name> full name of week day. e.g.: `Monday`, ...
        "m" - <Month number> in shortest possible way. e.g.: `1` if January
        "mm" - <Month number> with 2 digits.
        "mmm" - <Month name> shortened month name. e.g.: `Jan`, ...
        "mmmm" - <Month name> full month name. e.g.: `January`, ...
        "yy" - <Year number> shortened year. e.g.: `19`, `20`, ...
        "yyyy" - <Year number> full year. e.g.: `2019`, `2020`, ...
        "H" - <Hours number 24-hour> shortened hours.
        "HH" - <Hours number 24-hour> with 2 digits.
        "h" - <Hours number 12-hour> shortened hours.
        "hh" - <Hours number 12-hour> with 2 digits.
        "ht" - <Midday type> AM or PM.
        "M" - <Minutes number> shortened minutes.
        "MM" - <Minutes number> with 2 digits.
        "S" - <Seconds number> shortened seconds.
        "SS" - <Seconds number> with 2 digits.
    """

    if not datetime_obj:
        datetime_obj = datetime.datetime.now()

    year = datetime_obj.strftime("%Y")

    month = datetime_obj.strftime("%m")
    month_name_full = datetime_obj.strftime("%B")
    month_name_short = datetime_obj.strftime("%b")
    day = datetime_obj.strftime("%d")

    weekday_full = datetime_obj.strftime("%A")
    weekday_short = datetime_obj.strftime("%a")

    hours = datetime_obj.strftime("%H")
    hours_midday = datetime_obj.strftime("%I")
    hour_midday_type = datetime_obj.strftime("%p")
    minutes = datetime_obj.strftime("%M")
    seconds = datetime_obj.strftime("%S")

    return {
        "d": str(int(day)),
        "dd": str(day),
        "ddd": weekday_short,
        "dddd": weekday_full,
        "m": str(int(month)),
        "mm": str(month),
        "mmm": month_name_short,
        "mmmm": month_name_full,
        "yy": str(year[2:]),
        "yyyy": str(year),
        "H": str(int(hours)),
        "HH": str(hours),
        "h": str(int(hours_midday)),
        "hh": str(hours_midday),
        "ht": hour_midday_type,
        "M": str(int(minutes)),
        "MM": str(minutes),
        "S": str(int(seconds)),
        "SS": str(seconds),
    }


def get_formatted_current_time():
    return datetime.datetime.now().strftime(
        "%Y%m%dT%H%M%SZ"
    )
