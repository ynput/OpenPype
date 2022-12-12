import re
import logging

log = logging.getLogger(__name__)


def compile_list_of_regexes(in_list):
    """Convert strings in entered list to compiled regex objects."""
    regexes = list()
    if not in_list:
        return regexes

    for item in in_list:
        if not item:
            continue
        try:
            regexes.append(re.compile(item))
        except TypeError:
            print((
                "Invalid type \"{}\" value \"{}\"."
                " Expected string based object. Skipping."
            ).format(str(type(item)), str(item)))
    return regexes


def _profile_exclusion(matching_profiles, logger):
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


def fullmatch(regex, string, flags=0):
    """Emulate python-3.4 re.fullmatch()."""
    matched = re.match(regex, string, flags=flags)
    if matched and matched.span()[1] == len(string):
        return matched
    return None


def validate_value_by_regexes(value, in_list):
    """Validates in any regex from list match entered value.

    Args:
        value (str): String where regexes is checked.
        in_list (list): List with regexes.

    Returns:
        int: Returns `0` when list is not set, is empty or contain "*".
            Returns `1` when any regex match value and returns `-1`
            when none of regexes match entered value.
    """
    if not in_list:
        return 0

    if not isinstance(in_list, (list, tuple, set)):
        in_list = [in_list]

    if "*" in in_list:
        return 0

    # If value is not set and in list has specific values then resolve value
    #   as not matching.
    if not value:
        return -1

    regexes = compile_list_of_regexes(in_list)
    for regex in regexes:
        if hasattr(regex, "fullmatch"):
            result = regex.fullmatch(value)
        else:
            result = fullmatch(regex, value)
        if result:
            return 1
    return -1


def filter_profiles(profiles_data, key_values, keys_order=None, logger=None):
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
        logger (logging.Logger): Optionally can be passed different logger.

    Returns:
        dict/None: Return most matching profile or None if none of profiles
            match at least one criteria.
    """
    if not profiles_data:
        return None

    if not logger:
        logger = log

    if not keys_order:
        keys_order = tuple(key_values.keys())
    else:
        _keys_order = list(keys_order)
        # Make all keys from `key_values` are passed
        for key in key_values.keys():
            if key not in _keys_order:
                _keys_order.append(key)
        keys_order = tuple(_keys_order)

    log_parts = " | ".join([
        "{}: \"{}\"".format(*item)
        for item in key_values.items()
    ])

    logger.info(
        "Looking for matching profile for: {}".format(log_parts)
    )

    matching_profiles = None
    highest_profile_points = -1
    # Each profile get 1 point for each matching filter. Profile with most
    # points is returned. For cases when more than one profile will match
    # are also stored ordered lists of matching values.
    for profile in profiles_data:
        profile_points = 0
        profile_scores = []

        for key in keys_order:
            value = key_values[key]
            match = validate_value_by_regexes(value, profile.get(key))
            if match == -1:
                profile_value = profile.get(key) or []
                logger.debug(
                    "\"{}\" not found in \"{}\": {}".format(value, key,
                                                            profile_value)
                )
                profile_points = -1
                break

            profile_points += match
            profile_scores.append(bool(match))

        if (
            profile_points < 0
            or profile_points < highest_profile_points
        ):
            continue

        if profile_points > highest_profile_points:
            matching_profiles = []
            highest_profile_points = profile_points

        if profile_points == highest_profile_points:
            matching_profiles.append((profile, profile_scores))

    if not matching_profiles:
        logger.info(
            "None of profiles match your setup. {}".format(log_parts)
        )
        return None

    if len(matching_profiles) > 1:
        logger.info(
            "More than one profile match your setup. {}".format(log_parts)
        )

    profile = _profile_exclusion(matching_profiles, logger)
    if profile:
        logger.info(
            "Profile selected: {}".format(profile)
        )
    return profile
