import os
import re
import datetime
import uuid
import string
import platform
import collections
try:
    # Python 3
    from urllib.parse import urlparse, urlencode
except ImportError:
    # Python 2
    from urlparse import urlparse
    from urllib import urlencode

import requests
import unidecode

from .constants import (
    SERVER_TIMEOUT_ENV_KEY,
    DEFAULT_VARIANT_ENV_KEY,
    SITE_ID_ENV_KEY,
)
from .exceptions import UrlError

REMOVED_VALUE = object()
SLUGIFY_WHITELIST = string.ascii_letters + string.digits
SLUGIFY_SEP_WHITELIST = " ,./\\;:!|*^#@~+-_="

RepresentationParents = collections.namedtuple(
    "RepresentationParents",
    ("version", "product", "folder", "project")
)


def get_default_timeout():
    """Default value for requests timeout.

    First looks for environment variable SERVER_TIMEOUT_ENV_KEY which
    can affect timeout value. If not available then use 10.0 s.

    Returns:
        float: Timeout value in seconds.
    """

    try:
        return float(os.environ.get(SERVER_TIMEOUT_ENV_KEY))
    except (ValueError, TypeError):
        pass
    return 10.0


def get_default_settings_variant():
    """Default settings variant.

    Returns:
        str: Settings variant from environment variable or 'production'.
    """

    return os.environ.get(DEFAULT_VARIANT_ENV_KEY) or "production"


def get_default_site_id():
    """Site id used for server connection.

    Returns:
        Union[str, None]: Site id from environment variable or None.
    """

    return os.environ.get(SITE_ID_ENV_KEY)


class ThumbnailContent:
    """Wrapper for thumbnail content.

    Args:
        project_name (str): Project name.
        thumbnail_id (Union[str, None]): Thumbnail id.
        content_type (Union[str, None]): Content type e.g. 'image/png'.
        content (Union[bytes, None]): Thumbnail content.
    """

    def __init__(self, project_name, thumbnail_id, content, content_type):
        self.project_name = project_name
        self.thumbnail_id = thumbnail_id
        self.content_type = content_type
        self.content = content or b""

    @property
    def id(self):
        """Wrapper for thumbnail id.

        Returns:

        """

        return self.thumbnail_id

    @property
    def is_valid(self):
        """Content of thumbnail is valid.

        Returns:
            bool: Content is valid and can be used.
        """
        return (
            self.thumbnail_id is not None
            and self.content_type is not None
        )


def prepare_query_string(key_values):
    """Prepare data to query string.

    If there are any values a query starting with '?' is returned otherwise
    an empty string.

    Args:
         dict[str, Any]: Query values.

    Returns:
        str: Query string.
    """

    if not key_values:
        return ""
    return "?{}".format(urlencode(key_values))


def create_entity_id():
    return uuid.uuid1().hex


def convert_entity_id(entity_id):
    if not entity_id:
        return None

    if isinstance(entity_id, uuid.UUID):
        return entity_id.hex

    try:
        return uuid.UUID(entity_id).hex

    except (TypeError, ValueError, AttributeError):
        pass
    return None


def convert_or_create_entity_id(entity_id=None):
    output = convert_entity_id(entity_id)
    if output is None:
        output = create_entity_id()
    return output


def entity_data_json_default(value):
    if isinstance(value, datetime.datetime):
        return int(value.timestamp())

    raise TypeError(
        "Object of type {} is not JSON serializable".format(str(type(value)))
    )


def slugify_string(
    input_string,
    separator="_",
    slug_whitelist=SLUGIFY_WHITELIST,
    split_chars=SLUGIFY_SEP_WHITELIST,
    min_length=1,
    lower=False,
    make_set=False,
):
    """Slugify a text string.

    This function removes transliterates input string to ASCII, removes
    special characters and use join resulting elements using
    specified separator.

    Args:
        input_string (str): Input string to slugify
        separator (str): A string used to separate returned elements
            (default: "_")
        slug_whitelist (str): Characters allowed in the output
            (default: ascii letters, digits and the separator)
        split_chars (str): Set of characters used for word splitting
            (there is a sane default)
        lower (bool): Convert to lower-case (default: False)
        make_set (bool): Return "set" object instead of string.
        min_length (int): Minimal length of an element (word).

    Returns:
        Union[str, Set[str]]: Based on 'make_set' value returns slugified
            string.
    """

    tmp_string = unidecode.unidecode(input_string)
    if lower:
        tmp_string = tmp_string.lower()

    parts = [
        # Remove all characters that are not in whitelist
        re.sub("[^{}]".format(re.escape(slug_whitelist)), "", part)
        # Split text into part by split characters
        for part in re.split("[{}]".format(re.escape(split_chars)), tmp_string)
    ]
    # Filter text parts by length
    filtered_parts = [
        part
        for part in parts
        if len(part) >= min_length
    ]
    if make_set:
        return set(filtered_parts)
    return separator.join(filtered_parts)


def failed_json_default(value):
    return "< Failed value {} > {}".format(type(value), str(value))


def prepare_attribute_changes(old_entity, new_entity, replace=False):
    attrib_changes = {}
    new_attrib = new_entity.get("attrib")
    old_attrib = old_entity.get("attrib")
    if new_attrib is None:
        if not replace:
            return attrib_changes
        new_attrib = {}

    if old_attrib is None:
        return new_attrib

    for attr, new_attr_value in new_attrib.items():
        old_attr_value = old_attrib.get(attr)
        if old_attr_value != new_attr_value:
            attrib_changes[attr] = new_attr_value

    if replace:
        for attr in old_attrib:
            if attr not in new_attrib:
                attrib_changes[attr] = REMOVED_VALUE

    return attrib_changes


def prepare_entity_changes(old_entity, new_entity, replace=False):
    """Prepare changes of entities."""

    changes = {}
    for key, new_value in new_entity.items():
        if key == "attrib":
            continue

        old_value = old_entity.get(key)
        if old_value != new_value:
            changes[key] = new_value

    if replace:
        for key in old_entity:
            if key not in new_entity:
                changes[key] = REMOVED_VALUE

    attr_changes = prepare_attribute_changes(old_entity, new_entity, replace)
    if attr_changes:
        changes["attrib"] = attr_changes
    return changes


def _try_parse_url(url):
    try:
        return urlparse(url)
    except BaseException:
        return None


def _try_connect_to_server(url, timeout=None):
    if timeout is None:
        timeout = get_default_timeout()
    try:
        # TODO add validation if the url lead to Ayon server
        #   - this won't validate if the url lead to 'google.com'
        requests.get(url, timeout=timeout)

    except BaseException:
        return False
    return True


def login_to_server(url, username, password, timeout=None):
    """Use login to the server to receive token.

    Args:
        url (str): Server url.
        username (str): User's username.
        password (str): User's password.
        timeout (Optional[float]): Timeout for request. Value from
            'get_default_timeout' is used if not specified.

    Returns:
        Union[str, None]: User's token if login was successfull.
            Otherwise 'None'.
    """

    if timeout is None:
        timeout = get_default_timeout()
    headers = {"Content-Type": "application/json"}
    response = requests.post(
        "{}/api/auth/login".format(url),
        headers=headers,
        json={
            "name": username,
            "password": password
        },
        timeout=timeout,
    )
    token = None
    # 200 - success
    # 401 - invalid credentials
    # *   - other issues
    if response.status_code == 200:
        token = response.json()["token"]
    return token


def logout_from_server(url, token, timeout=None):
    """Logout from server and throw token away.

    Args:
        url (str): Url from which should be logged out.
        token (str): Token which should be used to log out.
        timeout (Optional[float]): Timeout for request. Value from
            'get_default_timeout' is used if not specified.
    """

    if timeout is None:
        timeout = get_default_timeout()
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(token)
    }
    requests.post(
        url + "/api/auth/logout",
        headers=headers,
        timeout=timeout,
    )


def is_token_valid(url, token, timeout=None):
    """Check if token is valid.

    Token can be a user token or service api key.

    Args:
        url (str): Server url.
        token (str): User's token.
        timeout (Optional[float]): Timeout for request. Value from
            'get_default_timeout' is used if not specified.

    Returns:
        bool: True if token is valid.
    """

    if timeout is None:
        timeout = get_default_timeout()

    base_headers = {
        "Content-Type": "application/json",
    }
    for header_value in (
        {"Authorization": "Bearer {}".format(token)},
        {"X-Api-Key": token},
    ):
        headers = base_headers.copy()
        headers.update(header_value)
        response = requests.get(
            "{}/api/users/me".format(url),
            headers=headers,
            timeout=timeout,
        )
        if response.status_code == 200:
            return True
    return False


def validate_url(url, timeout=None):
    """Validate url if is valid and server is available.

    Validation checks if can be parsed as url and contains scheme.

    Function will try to autofix url thus will return modified url when
    connection to server works.

    ```python
    my_url = "my.server.url"
    try:
        # Store new url
        validated_url = validate_url(my_url)

    except UrlError:
        # Handle invalid url
        ...
    ```

    Args:
        url (str): Server url.
        timeout (Optional[int]): Timeout in seconds for connection to server.

    Returns:
        Url which was used to connect to server.

    Raises:
        UrlError: Error with short description and hints for user.
    """

    stripperd_url = url.strip()
    if not stripperd_url:
        raise UrlError(
            "Invalid url format. Url is empty.",
            title="Invalid url format",
            hints=["url seems to be empty"]
        )

    # Not sure if this is good idea?
    modified_url = stripperd_url.rstrip("/")
    parsed_url = _try_parse_url(modified_url)
    universal_hints = [
        "does the url work in browser?"
    ]
    if parsed_url is None:
        raise UrlError(
            "Invalid url format. Url cannot be parsed as url \"{}\".".format(
                modified_url
            ),
            title="Invalid url format",
            hints=universal_hints
        )

    # Try add 'https://' scheme if is missing
    # - this will trigger UrlError if both will crash
    if not parsed_url.scheme:
        new_url = "https://" + modified_url
        if _try_connect_to_server(new_url, timeout=timeout):
            return new_url

    if _try_connect_to_server(modified_url, timeout=timeout):
        return modified_url

    hints = []
    if "/" in parsed_url.path or not parsed_url.scheme:
        new_path = parsed_url.path.split("/")[0]
        if not parsed_url.scheme:
            new_path = "https://" + new_path

        hints.append(
            "did you mean \"{}\"?".format(parsed_url.scheme + new_path)
        )

    raise UrlError(
        "Couldn't connect to server on \"{}\"".format(url),
        title="Couldn't connect to server",
        hints=hints + universal_hints
    )


class TransferProgress:
    """Object to store progress of download/upload from/to server."""

    def __init__(self):
        self._started = False
        self._transfer_done = False
        self._transferred = 0
        self._content_size = None

        self._failed = False
        self._fail_reason = None

        self._source_url = "N/A"
        self._destination_url = "N/A"

    def get_content_size(self):
        """Content size in bytes.

        Returns:
            Union[int, None]: Content size in bytes or None
                if is unknown.
        """

        return self._content_size

    def set_content_size(self, content_size):
        """Set content size in bytes.

        Args:
            content_size (int): Content size in bytes.

        Raises:
            ValueError: If content size was already set.
        """

        if self._content_size is not None:
            raise ValueError("Content size was set more then once")
        self._content_size = content_size

    def get_started(self):
        """Transfer was started.

        Returns:
            bool: True if transfer started.
        """

        return self._started

    def set_started(self):
        """Mark that transfer started.

        Raises:
            ValueError: If transfer was already started.
        """

        if self._started:
            raise ValueError("Progress already started")
        self._started = True

    def get_transfer_done(self):
        """Transfer finished.

        Returns:
            bool: Transfer finished.
        """

        return self._transfer_done

    def set_transfer_done(self):
        """Mark progress as transfer finished.

        Raises:
            ValueError: If progress was already marked as done
                or wasn't started yet.
        """

        if self._transfer_done:
            raise ValueError("Progress was already marked as done")
        if not self._started:
            raise ValueError("Progress didn't start yet")
        self._transfer_done = True

    def get_failed(self):
        """Transfer failed.

        Returns:
            bool: True if transfer failed.
        """

        return self._failed

    def get_fail_reason(self):
        """Get reason why transfer failed.

        Returns:
            Union[str, None]: Reason why transfer
                failed or None.
        """

        return self._fail_reason

    def set_failed(self, reason):
        """Mark progress as failed.

        Args:
            reason (str): Reason why transfer failed.
        """

        self._fail_reason = reason
        self._failed = True

    def get_transferred_size(self):
        """Already transferred size in bytes.

        Returns:
            int: Already transferred size in bytes.
        """

        return self._transferred

    def set_transferred_size(self, transferred):
        """Set already transferred size in bytes.

        Args:
            transferred (int): Already transferred size in bytes.
        """

        self._transferred = transferred

    def add_transferred_chunk(self, chunk_size):
        """Add transferred chunk size in bytes.

        Args:
            chunk_size (int): Add transferred chunk size
                in bytes.
        """

        self._transferred += chunk_size

    def get_source_url(self):
        """Source url from where transfer happens.

        Note:
            Consider this as title. Must be set using
                'set_source_url' or 'N/A' will be returned.

        Returns:
            str: Source url from where transfer happens.
        """

        return self._source_url

    def set_source_url(self, url):
        """Set source url from where transfer happens.

        Args:
            url (str): Source url from where transfer happens.
        """

        self._source_url = url

    def get_destination_url(self):
        """Destination url where transfer happens.

        Note:
            Consider this as title. Must be set using
                'set_source_url' or 'N/A' will be returned.

        Returns:
            str: Destination url where transfer happens.
        """

        return self._destination_url

    def set_destination_url(self, url):
        """Set destination url where transfer happens.

        Args:
            url (str): Destination url where transfer happens.
        """

        self._destination_url = url

    @property
    def is_running(self):
        """Check if transfer is running.

        Returns:
            bool: True if transfer is running.
        """

        if (
            not self.started
            or self.transfer_done
            or self.failed
        ):
            return False
        return True

    @property
    def transfer_progress(self):
        """Get transfer progress in percents.

        Returns:
            Union[float, None]: Transfer progress in percents or 'None'
                if content size is unknown.
        """

        if self._content_size is None:
            return None
        return (self._transferred * 100.0) / float(self._content_size)

    content_size = property(get_content_size, set_content_size)
    started = property(get_started)
    transfer_done = property(get_transfer_done)
    failed = property(get_failed)
    fail_reason = property(get_fail_reason)
    source_url = property(get_source_url, set_source_url)
    destination_url = property(get_destination_url, set_destination_url)
    transferred_size = property(get_transferred_size, set_transferred_size)


def create_dependency_package_basename(platform_name=None):
    """Create basename for dependency package file.

    Args:
        platform_name (Optional[str]): Name of platform for which the
            bundle is targeted. Default value is current platform.

    Returns:
        str: Dependency package name with timestamp and platform.
    """

    if platform_name is None:
        platform_name = platform.system().lower()

    now_date = datetime.datetime.now()
    time_stamp = now_date.strftime("%y%m%d%H%M")
    return "ayon_{}_{}".format(time_stamp, platform_name)
