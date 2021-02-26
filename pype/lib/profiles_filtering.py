import re
import logging
from .applications import compile_list_of_regexes

log = logging.getLogger(__name__)


def _profile_exclusion(matching_profiles):
    """Find out most matching profile byt host, task and family match.

    Profiles are selectively filtered. Each item in passed argument must
    contain tuple of (profile, profile's score) where score is list of
    booleans. Each boolean represents existence of filter for specific key.
    Profiles are looped in sequence. In each sequence are profiles split into
    true_list and false_list. For next sequence loop are used profiles in
    true_list if there are any profiles else false_list is used.

    Filtering ends when only one profile left in true_list. Or when all
    existence booleans loops passed, in that case first profile from remainded
    profiles is returned.

    Args:
        matching_profiles (list): Profiles with same scores. Each item is tuple
            with (profile, profile values)

    Returns:
        dict: Most matching profile.
    """
    log.info(
        "Search for first most matching profile in match order:"
        " Host name -> Task name -> Family."
    )
    # Filter all profiles with highest points value. First filter profiles
    # with matching host if there are any then filter profiles by task
    # name if there are any and lastly filter by family. Else use first in
    # list.
    if not matching_profiles:
        return None

    if len(matching_profiles) == 1:
        return matching_profiles[0][0]

    scores_len = len(matching_profiles[0][1])
    for idx in range(scores_len):
        profiles_true = []
        profiles_false = []
        for profile, score in matching_profiles:
            if score[idx]:
                profiles_true.append((profile, score))
            else:
                profiles_false.append((profile, score))

        if profiles_true:
            matching_profiles = profiles_true
        else:
            matching_profiles = profiles_false

        if len(matching_profiles) == 1:
            return matching_profiles[0][0]

    return matching_profiles[0][0]


def validate_value_by_regexes(value, in_list):
    """Validates in any regex from list match entered value.

    Args:
        in_list (list): List with regexes.
        value (str): String where regexes is checked.

    Returns:
        int: Returns `0` when list is not set or is empty. Returns `1` when
            any regex match value and returns `-1` when none of regexes
            match value entered.
    """
    if not in_list:
        return 0

    if not isinstance(in_list, (list, tuple, set)):
        in_list = [in_list]

    if "*" in in_list:
        return 0

    regexes = compile_list_of_regexes(in_list)
    for regex in regexes:
        if re.match(regex, value):
            return 1
    return -1


def filter_profiles(profiles_data, key_values, keys_order=None):
    """ Filter profiles by entered key -> values.

    Profile if marked with score for each key/value from `key_values` with
    points -1, 0 or 1.
    - if profile contain the key and profile's value contain value from
        `key_values` then profile gets 1 point
    - if profile does not contain the key or profile's value is empty or
        contain "*" then got 0 point
    - if profile contain the key, profile's value is not empty and does not
        contain "*" and value from `key_values` is not available in the value
        then got -1 point

    If profile gets -1 point at any time then is skipped and not used for
    output. Profile with higher score is returned. If there are multiple
    profiles with same score then first in order is used (order of profiles
    matter).

    Args:
        profiles_data (list): Profile definitions as dictionaries.
        key_values (dict): Mapping of Key <-> Value. Key is checked if is
            available in profile and if Value is matching it's values.
        keys_order (list, tuple): Order of keys from `key_values` which matters
            only when multiple profiles have same score.

    Returns:
        dict/None: Return most matching profile or None if none of profiles
            match at least one criteria.
    """

    if not profiles_data:
        return None

    if not keys_order:
        keys_order = tuple(key_values.keys())
    else:
        _keys_order = list(keys_order)
        # Make all keys from `key_values` are passed
        for key in key_values.keys():
            if key not in _keys_order:
                _keys_order.append(key)
        keys_order = tuple(_keys_order)

    matching_profiles = None
    highest_profile_points = -1
    # Each profile get 1 point for each matching filter. Profile with most
    # points is returned. For cases when more than one profile will match
    # are also stored ordered lists of matching values.
    for profile in profiles_data:
        profile_points = 0
        profile_value = []

        for key in keys_order:
            value = key_values[key]
            profile_value = profile.get(key) or []
            match = validate_value_by_regexes(value, profile.get(key))
            if match == -1:
                log.debug(
                    "\"{}\" not found in {}".format(key, profile_value)
                )
                continue

            profile_points += match
            profile_value.append(bool(match))

            if profile_points < highest_profile_points:
                continue

            if profile_points > highest_profile_points:
                matching_profiles = []
                highest_profile_points = profile_points

            if profile_points == highest_profile_points:
                matching_profiles.append((profile, profile_value))

    log_parts = " | ".join([
        "{}: \"{}\"".format(*item)
        for item in key_values.items()
    ])

    if not matching_profiles:
        log.warning("None of profiles match your setup. {}".format(log_parts))
        return None

    if len(matching_profiles) > 1:
        log.warning(
            "More than one profile match your setup. {}".format(log_parts)
        )

    return _profile_exclusion(matching_profiles)
